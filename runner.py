import enum
import time
import parser

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
    failure = 2

class Process:
    status: Status
    restart_policy: RestartPolicy

    stopped_at: int
    started_at: int

    pid: int
    numprocs: int
    max_numprocs: int
    autostart: bool
    initial_delay: int
    restarts: int
    graceful_period: int

    cmd: list
    exit_codes: list
    alternative_stdout: str
    alternative_stdin: str
    cwd: str

class Context:
    processes: dict

class Runner:
    context: Context
    parser: parser.Parser
    data: dict

    def __init__(self):
        self.context = Context()

        self.parser = parser.create_parser()

        self.data = self.parser.parse()

    def input(self):
        program = self.data["programs"]["program1"]

        process = Process()

        process.status = Status.NONE
        process.restart_policy = int(program[""])

    def loop(self):

        print("Command:", program["command"])

if __name__ == "__main__":
    runner = Runner()

    runner.loop()

