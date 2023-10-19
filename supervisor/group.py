import os
import sys
import enum
import signal
import tempfile
import threading
import logging

from typing import List, Dict, Any, Callable

from program import Program, Autorestart
from process import Process, ProcessState


class Group:
    _processes: Dict[str, Process]
    _program: Program

    def __init__(self, name: str, config: Dict[str, Any]):
        self._processes = dict()
        self._program = Program(config)

        for i in range(self._program.numprocs):
            self._processes[f"{name}:{i}"] = Process(program)

    def start(self, name: str = None):
        if name is None:
            for process in self._processes.values():
                if (process.state == ProcessState.stopped or 
                        process.state == ProcessState.fatal or 
                        process.state == ProcessState.exited):
                    process.spawn()
        elif name in self._processes.keys():
            process: Process = self._processes[name]

            if (process.state == ProcessState.stopped or 
                    process.state == ProcessState.fatal or 
                    process.state == ProcessState.exited):
                process.spawn()

    def stop(self, name: str = None, callback: Callable = None):
        if name is None:
            for process in self._processes.values():
                if process.state == ProcessState.starting or process.state == ProcessState.running
                    process.stop(callback)
        elif name in self._processes.keys():
            process = self._processes[name]

            if process.state == ProcessState.starting or process.state == ProcessState.running:
                process.stop(callback)

    def restart(self, name: str = None):
        def on_stop():
            self._start(name)

        self._stop(on_stop)

