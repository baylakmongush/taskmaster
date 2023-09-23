import enum

class Status(enum.Enum):
    starting = 0
    running = 1
    stopping = 2
    stopped = 3
    failed = 4


class RestartPolicy(enum.Enum):
    never = 0
    always = 1
    on_failure = 2


class Process:
    status: Status

    pid: int
    restarts: int
    started_at: int
    stopped_at: int
    last_exit_code: int

    owner: str
    

class ProcessGroup:
    autostart: bool

    restart_policy: RestartPolicy

    numprocs: int
    max_numprocs: int
    max_restarts: int
    initial_delay: int
    graceful_period: int
    permissions: int
    
    cwd: str
    exit_signal: str
    alternative_stdout: str
    alternative_stderr: str

    cmd: list
    exit_codes: list

    env: dict

    processes: dict

    def __init__(self):
        self.numprocs = 0

    def __str__(self):
        return f"Process group:\n\tautostart: {self.autostart}\n\trestart_policy: {self.restart_policy}\n\tnumprocs: {self.numprocs}\n\tmax_numprocs: {self.max_numprocs}\n\tmax_restarts: {self.max_restarts}\n\tinitial_delay: {self.initial_delay}\n\tgraceful_period: {self.graceful_period}\n\tpermissions: {oct(self.permissions)}\n\tcwd: {self.cwd}\n\texit_signal: {self.exit_signal}\n\talternative_stdout: {self.alternative_stdout}\n\talternative_stderr: {self.alternative_stderr}\n\tcmd: {self.cmd}\n\texit_codes: {self.exit_codes}\n\tenv: {self.env}"


