import os
import sys
import enum
import signal
import tempfile
import threading
import logging
import time

from typing import List, Dict, Any, Callable, Union

from .group import Group
from .context import Context
from .process import Process, ProcessState

class Taskmaster:
    _groups: Dict[str, Group]
    _config: Dict[str, Any]
    _logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self._groups = dict()
        self._config = dict()
        self._logger = logger

        signal.signal(signal.SIGCHLD, lambda s, f: self._sigchld_handler())

    def reload(self, config: Dict[str, Any]):
        removed = set(self._config.keys()) - set(config.keys())
        added = set(config.keys()) - set(self._config.keys())
        same = set(self._config.keys()) & set(config.keys())

        for group in removed:
            def on_stop(pid: int, group=group):
               if all(process.state in [ProcessState.stopped, ProcessState.exited, ProcessState.fatal] for process in self._groups[group].processes.values()): 
                    del self._groups[group]

            self.stop(group, None, on_stop)

        for group in added:
            self._groups[group] = Group(group, config[group], self._logger)

            self.start(group)

        for group in same:
            if self._config[group] != config[group]:
                def on_stop(pid: int, group=group):
                    if all(process.state in [ProcessState.stopped, ProcessState.exited, ProcessState.fatal] for process in self._groups[group].processes.values()): 
                        del self._groups[group]

                        self._groups[group] = Group(group, config[group], self._logger)

                        self.start(group)

                self.stop(group, None, on_stop)

        self._config = config

    def start(self, group_name: str, process_name: str = None, on_spawn: Callable[[int], None] = None, on_fail: Callable[[int], None] = None) -> bool:
        if group_name in self._groups.keys():
            if process_name is not None:
                return self._groups[group_name].start(process_name, on_spawn, on_fail)
            else:
                status = dict()

                for process in self._groups[group_name].processes.values():
                    status[process.name] = self._groups[group_name].start(process.name, on_spawn, on_fail)

                return status

        return False

    def stop(self, group_name: str, process_name: str = None, on_kill: Callable[[int], None] = None) -> bool:
        if group_name in self._groups.keys():
            if process_name is not None:
                return self._groups[group_name].stop(process_name, on_kill)
            else:
                status = dict()

                for process in self._groups[group_name].processes.values():
                    status[process.name] = self._groups[group_name].stop(process.name, on_kill)

                return status

        return False

    def restart(self, group_name: str, process_name: str = None, on_spawn: Callable[[int], None] = None) -> bool:
        if group_name in self._groups.keys():
            if process_name is not None:
                return self._groups[group_name].restart(process_name, on_spawn)
            else:
                status = dict()

                for process in self._groups[group_name].processes.values():
                    status[process.name] = self._groups[group_name].restart(process.name, on_spawn)

                return status

        return False

    def status(self, group_name: str, process_name: str = None) -> Union[Process, List[Process], None]:
        if group_name in self._groups.keys():
            if process_name is not None:
                return self._groups[group_name].status(process_name)
            else:
                status = list()

                for process in self._groups[group_name].processes.values():
                    status.append(self._groups[group_name].status(process.name))

                return status

        return None

    def pid(self, group_name: str, process_name: str) -> int:
        if group_name in self._groups.keys():
            if process_name in self._groups[group_name].processes.keys():
                return self._groups[group_name].processes[process_name].pid
        return -1

    def _sigchld_handler(self):
        try:
            pid, exit_code = os.waitpid(-1, os.WNOHANG)

            while pid > 0:
                process: Process = Context.get_process(pid)
        
                if process is not None:
                    threading.Thread(target=process.on_sigchld, args=[exit_code]).start()

                pid, exit_code = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            pass

