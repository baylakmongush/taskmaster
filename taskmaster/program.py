import enum
import signal

from typing import List, Dict, Any


class Autorestart(enum.Enum):
    true = 0, # Always reload the process
    unexpected = 1, # Reload only if the exit code is unexpected
    false = 2, # Never reload


class Program:
    stdout_logfile: str
    stderr_logfile: str
    startretries: int
    stopwaitsecs: int
    environment: Dict[str, str]
    autorestart: Autorestart
    stopsignal: signal.Signals
    exitcodes: List[int]
    autostart: bool
    directory: str
    startsecs: int
    numprocs: int
    command: List[str]
    umask: int

    def __init__(self, config: Dict[str, Any]):
        self.stdout_logfile = config.get("stdout", "AUTO") # Either AUTO, NONE or str
        self.stderr_logfile = config.get("stderr", "AUTO") # Either AUTO, NONE or str
        self.startretries = config.get("startretries", 3)
        self.stopwaitsecs = config.get("stopwaitsecs", 10)
        self.environment = config.get("environment", dict())
        self.autorestart = config.get("autorestart", Autorestart.unexpected)
        self.stopsignal = signal.Signals[config.get("stopsignal", "SIGTERM")].value
        self.exitcodes = config.get("exitcodes", [0])
        self.autostart = config.get("autostart", True)
        self.directory = config.get("directory", None) # None - do not chdir
        self.startsecs = config.get("startsecs", 1)
        self.numprocs = config.get("numprocs", 1)
        self.command = config.get("command", None).split() # Must be filled - error will be thrown otherwise
        self.umask = config.get("umask", None) # None - do not set umask
