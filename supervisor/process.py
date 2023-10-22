import os
import sys
import enum
import signal
import tempfile
import threading

from typing import List, Dict, Any, Callable

from program import Program, Autorestart


class ProcessState(enum.Enum):
    stopped = 0, # The process has been stopped due to a stop request or has never been started
    starting = 1, # The process is starting due to a start request
    running = 2, # The process is running
    backoff = 3, # The process entered the starting state but subsequently exited too quickly (before the time defined in startsecs) to move to the running state
    stopping = 4, # The process is stopping due to a stop request
    exited = 5, # The process exited from the RUNNING state (expectedly or unexpectedly)
    fatal = 6, # The process could not be started successfully
    unknown = 7 # The process is in an unknown state


class Process:
    """
    Represents actual process and provides interface to spawn/kill the process
    """
    _start_timer: threading.Timer
    _stop_timer: threading.Timer
    _on_spawn: Callable
    _restarts: int
    _on_kill: Callable
    _program: Program
    _state: ProcessState
    _lock: threading.Lock
    _name: str
    _pid: int

    def __init__(self, name: str, program: Program):
        self._start_timer = None
        self._stop_timer = None
        self._on_spawn = None
        self._restarts = 0
        self._on_kill = None
        self._program = program
        self._state = ProcessState.stopped
        self._lock = threading.Lock()
        self._name = name
        self._pid = 0

        print(f"Process '{self._name}' initialized")

    def spawn(self, on_spawn: Callable[[int], int] = None) -> bool:
        """
        This method will ALWAYS spawn new process, rewriting the state, 
            so be careful with it and make sure to check the state before spawning
        You MUST check for process state before spawning, make sure that the process is in
            stopped, exited or fatal state, otherwise you're violating the design
        """
        print(f"Spawning '{self._name}' process")

        self._start_timer = threading.Timer(self._program.startsecs, self._start_handler)
        self._on_spawn = on_spawn if on_spawn is not None else self._on_spawn
        self._state = ProcessState.starting if self._program.startsecs > 0 else ProcessState.running

        try:
            self._pid = os.fork()
        except Exception as error:
            print(f"Can't spawn '{self._name}' process due to an error:", error)

            return False

        if self._pid == 0:
            self._redirect_fd_into_logfile(sys.stdout.fileno(), self._program.stdout_logfile, ".stdout")
            self._redirect_fd_into_logfile(sys.stderr.fileno(), self._program.stderr_logfile, ".stderr")

            try:
                os.chdir(self._program.directory)
            except Exception:
                pass

            try:
                os.umask(self._program.umask)
            except Exception:
                pass

            os.execvpe(self._program.command[0], self._program.command, self._program.environment)
        else:
            self._start_timer.start() if self._program.startsecs > 0 else None

        return True

    def on_sigchld(self, exit_code: int):
        """
        Designed for external call from supervisor.
        """
        with self._lock:
            if self._state == ProcessState.starting:
                print(f"Process '{self._name}' died before it was considered started with code:", exit_code)

                self._state = ProcessState.backoff

                self._start_timer.cancel() if self._start_timer is not None else None

                if self._restarts < self._program.startretries:
                    self._restarts += 1

                    print(f"Process '{self._name}' will be restarted in '{self._restarts}' seconds")

                    threading.Timer(self._restarts, self.spawn).start()
                else:
                    print(f"Process '{self._name}' failed to start")

                    self._state = ProcessState.fatal
                    self._restarts = 0
            elif self._state == ProcessState.running:
                print(f"Running process '{self._name}' exited with code: {exit_code}. Expected: {exit_code in self._program.exitcodes}")

                self._state = ProcessState.exited

                if self._program.autorestart == Autorestart.true:
                    print(f"Process '{self._name}' will be restarted due to autostart policy")

                    self.spawn()
                elif self._program.autorestart == Autorestart.unexpected:
                    if exit_code not in self._program.exitcodes:
                        print(f"Process '{self._name}' will be restarted due to unexpected restart policy")

                    self.spawn() if exit_code not in self._program.exitcodes else None
            elif self._state == ProcessState.stopping:
                print(f"Process '{self._name}' has been stopped")

                self._state = ProcessState.stopped
                self._stop_handler.cancel() if self._stop_handler is not None else None
                self._pid = 0

                threading.Thread(target=self._on_kill, args=[self._pid]).start() if self._on_kill is not None else None
            else:
                print(f"Process '{self._name}' stopped with unknown state")

                self._state = ProcessState.unknown

    def kill(self, on_kill: Callable[[int], int] = None) -> bool:
        """
        This method is protected with lock because of sigchld signal 
            which could be running at the same time, graceful shutdown first,
            then sigkill after stopwaitsecs
        Could be executed only if the process is in starting or running states
        """
        with self._lock:
            if process.state != ProcessState.starting and process.state != ProcessState.running:
                return False

            self._start_timer.cancel() if self._start_timer is not None else None

            self._stop_timer = threading.Timer(self._program.stopwaitsecs, self._stop_handler)
            self._on_kill = on_kill if on_kill is not None else self._on_kill
            self._state = ProcessState.stopping

            try:
                os.kill(self._pid, self._program.stopsignal)
            except Exception:
                return False

            self._stop_timer.start()

            return True

    @property
    def state(self):
        return self._state

    def _redirect_fd_into_logfile(self, fd: int, logfile: str, suffix=""):
        file = None

        if logfile == "AUTO":
            file = tempfile.NamedTemporaryFile(mode="w", delete=False, prefix=self._name, suffix=suffix)
        elif logfile == "NONE":
            file = open("/dev/null", "w")
        else:
            try:
                file = open(logfile, "w")
            except Exception:
                file = open("/dev/null", "w")

        os.dup2(file.fileno(), fd)

    def _start_handler(self):
        with self._lock:
            print(f"Started handler invoked for '{self._name}' process")

            if self._state == ProcessState.starting:
                self._state = ProcessState.running
                self._restarts = 0

                threading.Thread(target=self._on_spawn, args=[self._pid]).start() if self._on_spawn is not None else None

    def _stop_handler(self):
        with self._lock:
            print(f"Stopped handler invoked for '{self._name}' process")

            if self._state == ProcessState.stopping:
                os.kill(self._pid, signal.Signals.SIGKILL)


if __name__ == "__main__":
    program = Program(dict())

    program.command = ["python3", "./processes/randomly_fails.py", "3"]
    #program.autorestart = Autorestart.true

    process = Process("sleep0", program)

    process.spawn()

    def func():
        pid, exit_code = os.waitpid(-1, os.WNOHANG)

        threading.Thread(target=process.on_sigchld, args=[exit_code]).start()

    signal.signal(signal.SIGCHLD, lambda s, f: func())

    while (True):
        pass
