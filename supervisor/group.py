import logging

from typing import Dict, Any, Callable

from program import Program
from process import Process, ProcessState


class Group:
    _pid_to_process: Dict[int, Process]
    _processes: Dict[str, Process]
    _program: Program
    _logger: logging.Logger

    def __init__(self, name: str, config: Dict[str, Any], logger: logging.Logger):
        self._pid_to_process = dict()
        self._processes = dict()
        self._program = Program(config)
        self._logger = logger

        for i in range(self._program.numprocs):
            self._processes[f"{name}:{i}"] = Process(program)

    def start(self, name: str) -> bool:
        if name in self._processes.keys():
            process: Process = self._processes[name]

            if (process.state == ProcessState.stopped or 
                    process.state == ProcessState.fatal or 
                    process.state == ProcessState.exited):
                pid: int = process.spawn()

                self._pid_to_process[pid] = process

                return True

        return False

    def stop(self, name: str, callback: Callable = None) -> bool:
        if name in self._processes.keys():
            return self._processes[name].stop(callback)

        return False

    def restart(self, name: str = None):
        self._stop(lambda: self._start(name))

    def on_sigchld(self, pid: int, exit_code: int):
        if pid in self._pid_to_process.keys():
            self._pid_to_process[pid].on_sigchld(exit_code)

