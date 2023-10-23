import os
import sys
import enum
import signal
import tempfile
import threading
import logging
import time

from typing import List, Dict, Any, Callable

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import parser

from .group import Group
from .context import Context


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

        for group in added:
            self._groups[group] = Group(group, config[group], self._logger)
            self.start(group)

    def start(self, group_name: str, process_name: str = None, on_spawn: Callable[[int], None] = None) -> None:
        if group_name in self._groups.keys():
            if process_name is not None:
                self._groups[group_name].start(process_name, on_spawn)
            else:
                for process in self._groups[group_name].processes.values():
                    self._groups[group_name].start(process.name, on_spawn)

    def stop(self, group_name: str, process_name: str = None, on_kill: Callable[[int], None] = None) -> None:
        if group_name in self._groups.keys():
            if process_name is not None:
                self._groups[group_name].stop(process_name, on_kill)
            else:
                for process in self._groups[group_name].processes.values():
                    self._groups[group_name].stop(process.name, on_kill)

    def restart(self, group_name: str, process_name: str = None, on_spawn: Callable[[int], None] = None) -> None:
        if group_name in self._groups.keys():
            if process_name is not None:
                return self._groups[group_name].restart(process_name, on_spawn)
            else:
                for process in self._groups[group_name].processes.values():
                    self._groups[group_name].restart(process.name, on_spawn)

    def status(self, group_name: str, process_name: str = None):
        if group_name in self._groups.keys():
            if process_name is not None:
                return self._groups[group_name].status(process_name)
            else:
                status = list()

                for process in self._groups[group_name].processes.values():
                    status.append(self._groups[group_name].status(process.name))

                return status

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


def setup_logger():
    # Define the logging format
    log_format = "%(asctime)s [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Log everything to the console
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


if __name__ == "__main__":
    prs = parser.create_parser()

    logger = setup_logger()

    taskmaster = Taskmaster(logger)

    config = prs.parse()["programs"]

    taskmaster.reload(config)

    while True:
        time.sleep(1)
