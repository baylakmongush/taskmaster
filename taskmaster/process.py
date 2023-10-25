import os
import sys
import enum
import signal
import tempfile
import threading
import logging
import time

from typing import List, Dict, Any, Callable

from .program import Program, Autorestart
from .context import Context


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
    _timestamp: int
    _on_spawn: Callable
    _restarts: int
    _on_kill: Callable
    _program: Program
    _logger: logging.Logger
    _state: ProcessState
    _lock: threading.Lock
    _name: str
    _pid: int

    def __init__(self, name: str, program: Program, logger: logging.Logger):
        self._name = name

        self._start_timer = None
        self._stop_timer = None
        self._timestamp = 0
        self._on_spawn = None
        self._restarts = 0
        self._on_fail = None
        self._on_kill = None
        self._program = program
        self._logger = logger
        self._state = ProcessState.stopped
        self._lock = threading.Lock()
        self._pid = 0

    def spawn(self, on_spawn: Callable[[int], None] = None, on_fail: Callable[[int], None] = None) -> bool:
        """
        This method will ALWAYS spawn new process, rewriting the state, 
            so be careful with it and make sure to check the state before spawning
        You MUST check for process state before spawning, make sure that the process is in
            stopped, exited or fatal state, otherwise you're violating the design
        """
        self._start_timer = threading.Timer(self._program.startsecs, self._start_handler)
        self._on_spawn = on_spawn if on_spawn is not None else self._on_spawn
        self._on_fail = on_fail if on_fail is not None else self._on_fail
        self._state = ProcessState.starting if self._program.startsecs > 0 else ProcessState.running

        try:
            self._pid = os.fork()
        except Exception as error:
            self._logger.critical(f"process {self._name} cannot be spawned due to an error: ", error)

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
            self._logger.info(f"spawned: {self._name} with pid {self._pid}")

            self._start_timer.start() if self._program.startsecs > 0 else None

            Context.insert_process(self._pid, self)

        return True

    def on_sigchld(self, exit_code: int):
        """
        Designed for external call from supervisor.
        """
        with self._lock:
            if self._state == ProcessState.starting:
                self._logger.warning(f"backoff: process {self._name} died before (startsecs) with exit_code: {exit_code}")

                self._state = ProcessState.backoff

                self._start_timer.cancel() if self._start_timer is not None else None

                if self._restarts < self._program.startretries:
                    self._restarts += 1

                    threading.Timer(self._restarts, self.spawn).start()
                else:
                    self._logger.error(f"fatal: process {self._name} failed to start, last exit_code: {exit_code}")

                    self._state = ProcessState.fatal
                    self._restarts = 0

                    threading.Thread(target=self._on_fail, args=[self._pid]).start() if self._on_fail is not None else None

            elif self._state == ProcessState.running:
                self._logger.info(f"stopped: process {self._name} pid {self._pid} exited with exit_code {exit_code}, expected: {exit_code in self._program.exitcodes}")

                self._state = ProcessState.exited

                if self._program.autorestart == Autorestart.true:
                    self._logger.info(f"restarting: process {self._name} configured to be always restarted, restarting...")

                    self.spawn()
                elif self._program.autorestart == Autorestart.unexpected:
                    if exit_code not in self._program.exitcodes:
                        self._logger.warning(f"restarting: process {self._name} exited with unexpected exit code, restaring...")

                        self.spawn()
            elif self._state == ProcessState.stopping:
                self._logger.info(f"stopped: process {self._name} successfully stopped")

                self._state = ProcessState.stopped

                self._stop_timer.cancel() if self._stop_handler is not None else None

                threading.Thread(target=self._on_kill, args=[self._pid]).start() if self._on_kill is not None else None

                self._pid = 0
            else:
                self._logger.critical(f"process {self._name} end up in unknown state")

                self._state = ProcessState.unknown

    def kill(self, on_kill: Callable[[int], int] = None) -> bool:
        """
        This method is protected with lock because of sigchld signal 
            which could be running at the same time, graceful shutdown first,
            then sigkill after stopwaitsecs
        Could be executed only if the process is in starting or running states
        """
        with self._lock:
            if self._state != ProcessState.starting and self._state != ProcessState.running:
                return False

            self._start_timer.cancel() if self._start_timer is not None else None

            self._stop_timer = threading.Timer(self._program.stopwaitsecs, self._stop_handler)
            self._on_kill = on_kill if on_kill is not None else self._on_kill
            self._state = ProcessState.stopping

            self._stop_timer.start()

            try:
                os.kill(self._pid, self._program.stopsignal)
            except Exception:
                return False

            return True

    @property
    def state(self):
        return self._state
    
    @property
    def name(self):
        return self._name

    @property
    def pid(self):
        return self._pid

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
            if self._state == ProcessState.starting:
                self._logger.info(f"success: {self._name} entered RUNNING state, process has stayed up for > than {self._program.startsecs} seconds (startsecs)")

                self._state = ProcessState.running
                self._restarts = 0
                self._timestamp = time.time()

                threading.Thread(target=self._on_spawn, args=[self._pid]).start() if self._on_spawn is not None else None

    def _stop_handler(self):
        with self._lock:
            if self._state == ProcessState.stopping:
                self._logger.warning(f"stopped: process {self._name} didn't stopped in time, sending sigkill")

                try:
                    os.kill(self._pid, signal.Signals.SIGKILL)
                except:
                    pass

    def __str__(self):
        return f"{self._state.name} {self._name} pid {self._pid} uptime {time.time() - self._timestamp}s"
