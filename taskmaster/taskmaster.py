import os
import sys
import enum
import signal
import tempfile
import threading
import logging
import time

from typing import List, Dict, Any, Callable, Union, Tuple

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

            for process in self._groups[group].processes.values():
                self._groups[group].stop(process.name, on_stop)

        for group in added:
            self._groups[group] = Group(group, config[group], self._logger)

            for process in self._groups[group].processes.values():
                self._groups[group].start(process.name)

        for group in same:
            if self._config[group] != config[group]:
                def on_stop(pid: int, group=group):
                    if all(process.state in [ProcessState.stopped, ProcessState.exited, ProcessState.fatal] for process in self._groups[group].processes.values()): 
                        del self._groups[group]

                        self._groups[group] = Group(group, config[group], self._logger)

                        for process in self._groups[group].processes.values():
                            self._groups[group].start(process.name)

                for process in self._groups[group].processes.values():
                    self._groups[group].stop(process.name, on_stop)

        self._config = config

    def start(self, group_name: str, process_name: str = None) -> Dict[str, Tuple[int, bool]] | None:
        if group_name in self._groups.keys():
            process_count = 0
            result = dict()
            lock = threading.Lock()

            def on_spawn(name: str, pid: int):
                nonlocal process_count

                with lock:
                    result[name] = (pid, True)
                    process_count -= 1

            def on_fail(name: str, pid: int):
                nonlocal process_count

                with lock:
                    result[name] = (pid, False)
                    process_count -= 1

            if process_name is not None:
                result[process_name] = (0, False)

                if self._groups[group_name].start(process_name, on_spawn, on_fail):
                    process_count += 1
            else:
                for process in self._groups[group_name].processes.values():
                    result[process.name] = (0, False)

                    if self._groups[group_name].start(process.name, on_spawn, on_fail):
                        process_count += 1

            while process_count != 0:
                time.sleep(0.1)

            return result
        return None

    def stop(self, group_name: str, process_name: str = None) -> Dict[str, Tuple[int, bool]] | None:
        if group_name in self._groups.keys():
            process_count = 0
            result = dict()
            lock = threading.Lock()

            def on_kill(name: str, pid: int):
                nonlocal process_count

                with lock:
                    result[name] = (pid, True)
                    process_count -= 1

            if process_name is not None:
                result[process_name] = (0, False)

                if self._groups[group_name].stop(process_name, on_kill):
                    process_count += 1
            else:
                for process in self._groups[group_name].processes.values():
                    result[process.name] = (0, False)

                    if self._groups[group_name].stop(process.name, on_kill):
                        process_count += 1

            while process_count != 0:
                time.sleep(0.1)

            return result
        return None

    def restart(self, group_name: str, process_name: str = None) -> Dict[str, Tuple[int, bool]] | None:
        if group_name in self._groups.keys():
            process_count = 0
            result = dict()
            lock = threading.Lock()

            def on_spawn(name: str, pid: int):
                nonlocal process_count

                with lock:
                    result[name] = (pid, True)
                    process_count -= 1

            def on_fail(name: str, pid: int):
                nonlocal process_count

                with lock:
                    result[name] = (pid, False)
                    process_count -= 1

            if process_name is not None:
                result[process_name] = (0, False)

                if self._groups[group_name].restart(process_name, on_spawn, on_fail):
                    process_count += 1
            else:
                for process in self._groups[group_name].processes.values():
                    result[process.name] = (0, False)

                    if self._groups[group_name].restart(process.name, on_spawn, on_fail):
                        process_count += 1

            while process_count != 0:
                time.sleep(0.1)

            return result
        return None

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

    def attach(self, group_name: str, process_name: str) -> None | str:
        if group_name not in self._groups.keys():
            return None

        if process_name not in self._groups[group_name].processes.keys():
            return None

        current_position = 0
        filename = self._groups[group_name].program.stdout_logfile

        while True:
            if os.path.getsize(filename) > current_position:
                try:
                    with open(filename, 'r') as file:
                        file.seek(current_position)
                        
                        new_logs = file.read()

                        current_position = file.tell()

                        yield new_logs
                except Exception:
                    yield None
            else:
                yield ""

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

