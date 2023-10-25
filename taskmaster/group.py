import os
import signal
import threading
import logging
import time

from typing import Dict, Any, Callable

from .program import Program
from .process import Process, ProcessState

class Group:
    processes: Dict[str, Process]
    name: str

    _program: Program
    _logger: logging.Logger

    def __init__(self, name: str, config: Dict[str, Any], logger: logging.Logger):
        self.processes = dict()
        self.name = name

        self._program = Program(config)
        self._logger = logger

        for i in range(self._program.numprocs):
            self.processes[f"{self.name}{i}"] = Process(f"{self.name}{i}", self._program, logger)

    def start(self, name: str, on_spawn: Callable[[int], None] = None, on_fail: Callable[[int], None] = None) -> bool:
        if name in self.processes.keys():
            process: Process = self.processes[name]

            if (process.state == ProcessState.stopped or 
                    process.state == ProcessState.fatal or 
                    process.state == ProcessState.exited):

                return process.spawn(on_spawn, on_fail)

        return False

    def stop(self, name: str, on_kill: Callable[[int], None] = None) -> bool:
        if name in self.processes.keys():
            return self.processes[name].kill(on_kill)

        return False

    def restart(self, name: str, on_spawn: Callable[[int], None] = None) -> bool:
        def _on_kill(pid: int):
            self.start(name, on_spawn)

        if not self.stop(name, _on_kill):
            return self.start(name, on_spawn)

    def status(self, name: str) -> Process:
        if name in self.processes.keys():
            return self.processes[name]

        return None
