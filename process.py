import enum


class Status(enum.Enum):
    none = 0
    starting = 1
    running = 2
    stopping = 3
    stopped = 4
    failed = 5


class RestartPolicy(enum.Enum):
    never = 0
    always = 1
    on_failure = 2


class Process:
    status: Status

    pid: int
    restarts: int
    started_at: int

    normal_exit_codes: list

    def __init__(self, normal_exit_codes: list):
        self.status = Status.none
        self.pid = 0
        self.restarts = 0
        self.normal_exit_codes = normal_exit_codes

    def __str__(self):
        return ", ".join("%s: %s" % i for i in vars(self).items())
    

class ProcessGroup:
    autostart: bool
    restart_policy: RestartPolicy
    umask: int
    numprocs: int
    restarts: int
    initial_delay: int
    graceful_period: int
    cwd: str
    exit_signal: str
    alternative_stdout: str
    alternative_stderr: str
    cmd: list
    env: dict
    processes: list

    def __init__(self, config: dict):
        self.autostart = config["autostart"]
        self.restart_policy = self._restart_policy_from_string(config["autorestart"])
        self.umask = int(config["umask"], 8)
        self.numprocs = config["numprocs"]
        self.restarts = config["startretries"]
        self.initial_delay = config["startsecs"]
        self.graceful_period = config["stopwaitsecs"]
        self.cwd = config["workingdir"]
        self.exit_signal = config["stopsignal"]
        self.alternative_stdout = config["stdout"]
        self.alternative_stderr = config["stderr"]
        self.cmd = config["command"].split()
        self.env = config["environment"]
        self.processes = [Process(config["exitcodes"]) for i in range(config["numprocs"])]

    def _restart_policy_from_string(self, string):
        for i in RestartPolicy:
            if i.name == string:
                return i

        return None

    def __str__(self):
        return "\n".join("%s: %s" % (k, str([str(i) for i in v]) if isinstance(v, list) else v) for (k, v) in vars(self).items())
