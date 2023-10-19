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
    _callback: Callable
    _restarts: int
    _program: Program
    _state: ProcessState
    _lock: threading.Lock
    _pid: int

    def __init__(self, program: Program):
        self._callback = None
        self._restarts = 0
        self._program = program
        self._state = ProcessState.stopped
        self._lock = threading.Lock
        self._pid = 0

    def spawn(self) -> int:
        self._pid = os.fork()

        if self._pid == 0:
            _redirect_fd_into_logfile(sys.stdout.fileno(), self._program.stdout_logfile)
            _redirect_fd_into_logfile(sys.stderr.fileno(), self._program.stderr_logfile)

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
            with self._lock:
                self._state = ProcessState.starting if self._program.startsecs > 0 else ProcessState.running

                def _initial_delay_handler():
                    with self._lock:
                        if self._state == ProcessState.starting:
                            self._state = ProcessState.running
                            self._restarts = 0

                if self._program.startsecs > 0:
                    threading.Timer(self._program.startsecs, lambda: _initial_delay_handler()).start()

            return self._pid

    def stop(self, callback: Callable = None):
        with self._lock:
            self._callback = callback
            self._restarts = 0
            self._state = ProcessState.stopping

            try:
                os.kill(self._pid, self._program.stopsignal)
            except Exception:
                pass

            def _graceful_shutdown_handler():
                with self._lock:
                    if self._state == ProcessState.stopping:
                        os.kill(self._pid, signal.Signals.SIGKILL)

            threading.Timer(self._program.stopwaitsecs, lambda: _graceful_shutdown_handler()).start()

    def on_sigchld(self, exit_code: int):
        with self._lock:
            if self._state == ProcessState.starting:
                self._state = ProcessState.backoff

                if self._restarts < self._program.startretries:
                    self._restarts += 1

                    threading.Timer(self._restarts, lambda: self.spawn())
                else:
                    self._state = ProcessState.fatal
            elif self._state == ProcessState.running:
                self._state = ProcessState.exited

                if self._program.autorestart == Autorestart.true:
                    self.spawn()
                elif self._program.autorestart == Autorestart.unexpected:
                    self.spawn() if exit_code not in self._program.exitcodes else None
            elif self._state == ProcessState.stopping:
                self._state = ProcessState.stopped

                if self._callback is not None:
                    self._callback()
            else:
                self._state = ProcessState.unknown

    @property
    def state(self):
        return self._state

    def _redirect_fd_into_logfile(self, fd: int, logfile: str):
        file = None

        if logfile == "AUTO":
            file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        elif logfile == "NONE":
            file = open("/dev/null", "w")
        else:
            try:
                file = open(logfile, "w")
            except FileNotFoundError:
                file = open("/dev/null", "w")
        
        os.dup2(file.fileno(), fd)

