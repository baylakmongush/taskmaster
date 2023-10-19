import os
import sys
import enum
import signal
import tempfile
import threading
import logging

from typing import List, Dict, Any


class Supervisor:
    _processes: Dict[str, Process]
    _groups: Dict[str, Group]
    _config: Dict[str, Any]
    _logger: logging.Logger

    _pid_to_process: Dict[int, Process]
    _pid_to_group: Dict[int, Group]

    def __init__(self, logger: logging.Logger):
        self._processes = list()
        self._groups = dict()
        self._config = dict()
        self._logger = logger
    
    def reload_config(self, config: Dict[str, Any]):
        self._logger.info("Updating runner configuration...")

        

    def start(self, name: str):
        pass

    def stop(self, name: str):
        pass

    def status(self, name: str):
        pass

    def restart(self, name: str):
        pass

    def _sigchld_handler(self):
        def _handler():
            pass

        threading.Thread(target=_handler).start()

    def _spawn_process(self, group: Group, name: str) -> Process:
        pid = os.fork()

        if pid == 0:
            _redirect_fd_into_logfile(group, sys.stdout.fileno(), group.stdout_logfile, name, ".stdout")
            _redirect_fd_into_logfile(group, sys.stderr.fileno(), group.stderr_logfile, name, ".stderr")

            try:
                os.chdir(group.directory)
            except Exception:
                pass

            try:
                os.umask(group.umask)
            except Exception:
                pass

            signal.signal(group.stopsignal, lambda s, f: sys.exit(group.exitcodes[0]))

            os.execvpe(group.command[0], group.command, group.environment)
        else:
            self._logger.info(f"spawned: '{process.name}' with pid {pid}")

            self._processes[pid] = Process(group, name, ProcessState.starting if group.startsecs > 0 else ProcessState.running, pid)

            if group.startsecs > 0:
                threading.Timer(group.startsecs, lambda: self._initial_delay_handler(process)).start()

            return self._processes[pid]

    def _stop_process(self, process: Process):
        process.state = ProcessState.stopping if process.group.stopwaitsecs > 0 else ProcessState.stopped

        self._kill_process(process, process.group.stopsignal)

        if process.group.stopwaitsecs > 0:
            threading.Timer(process.group.stopwaitsecs, lambda: self._graceful_shutdown_handler(process))

    def _redirect_fd_into_logfile(self, group: Group, fd: int, logfile: str, prefix: str = "", suffix: str = ""):
        file = None

        if logfile == "AUTO":
            file = tempfile.NamedTemporaryFile(mode="w", prefix=prefix, suffix=suffix, delete=False)
        else if logfile == "NONE":
            file = open("/dev/null", "w")
        else:
            try:
                file = open(logfile, "w")
            except FileNotFoundError:
                file = open("/dev/null", "w")
        
        os.dup2(file.fileno(), fd)

    def _initial_delay_handler(self, process: Process):
        if process.state == ProcessState.starting:
            process.state = ProcessState.running

    def _graceful_shutdown_handler(self, process: Process):
        if process.state == ProcessState.stopping:
            self._kill_process(process, signal.Signals.SIGKILL)

    def _kill_process(self, process: Process, signal: signal.Signals):
        try:
            os.kill(process.pid, signal)
        except Exception:
            pass
