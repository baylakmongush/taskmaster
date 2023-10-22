import os
import sys
import enum
import signal
import tempfile
import threading
import logging

from typing import List, Dict, Any

from .group import Group


class Taskmaster:
    _groups: Dict[str, Group] # Key == group_name

    _config: Dict[str, Any]
    _logger: logging.Logger

    _pid_to_group: Dict[int, Group]

    def __init__(self, logger: logging.Logger):
        self._groups = dict()
        self._config = dict()
        self._logger = logger

        signal.signal(signal.SIGCHLD, lambda s, f: self._sigchld_handler())

    def start(self, name: str) -> bool:
        """
        Name in format {group}:{process}
        """
        try:
            group, process = name.split(":")
        except Exception:
            _logger.error("usage error: unknown group/process")

            return False

        if group is not in self._groups.keys():
            _logger.error("usage error: unknown group")

            return False

        return self._groups[group].start(process)

    def stop(self, name: str = None):
        pass

    def reload(self, name: str = None):
        pass

    def status(self, name: str = None):
        pass

    def _sigchld_handler(self):
        def _handler():
            while True:
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)

                    if pid == 0:
                        break
                except OSError:
                    pass

        threading.Thread(target=_handler).start()
