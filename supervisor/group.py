import os
import signal
import threading
import logging
import time

from typing import Dict, Any, Callable

from program import Program
from process import Process, ProcessState
from context import Context

class Group:
    _processes: Dict[str, Process]
    _program: Program
    _logger: logging.Logger
    _name: str

    def __init__(self, name: str, config: Dict[str, Any], logger: logging.Logger):
        self._processes = dict()
        self._program = Program(config)
        self._logger = logger
        self._name = name

        for i in range(self._program.numprocs):
            self._processes[f"{name}{i}"] = Process(f"{name}{i}", self._program, logger)

    def start(self, name: str, on_spawn: Callable[[int], None] = None) -> bool:
        if name in self._processes.keys():
            process: Process = self._processes[name]

            if (process.state == ProcessState.stopped or 
                    process.state == ProcessState.fatal or 
                    process.state == ProcessState.exited):

                return process.spawn(on_spawn)

        return False

    def stop(self, name: str, on_kill: Callable[[int], None] = None) -> bool:
        if name in self._processes.keys():
            return self._processes[name].kill(on_kill)

        return False

    def restart(self, name: str = None, on_spawn: Callable[[int], None] = None):
        def _on_kill(pid):
            self.start(name, on_spawn)

        if not self.stop(name, _on_kill):
            return self.start(name, on_spawn)

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
    logger = setup_logger()

    config = dict()

    config["command"] = ["sleep", "360"] 
    config["numprocs"] = 3

    group = Group("sleep", config, logger)

    def func():
        try:
            pid, exit_code = os.waitpid(-1, os.WNOHANG)

            while pid > 0:
                process: Process = Context.get_process(pid)
        
                if process is not None:
                    threading.Thread(target=process.on_sigchld, args=[exit_code]).start()

                pid, exit_code = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            pass

    signal.signal(signal.SIGCHLD, lambda s, f: func())

    for i in group._processes.values():
        group.start(i._name, None)

    time.sleep(5)

    def on_reload(pid):
        print(f"process {pid} reloaded")

    for i in group._processes.values():
        group.restart(i._name, on_reload)

    while (True):
        time.sleep(1)
