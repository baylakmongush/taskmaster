import os
import sys
import enum
import signal

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

class Mark(enum.Enum):
    none = 0
    delete_requested = 1
    restart_requested = 2

class ProcessInstance:
    status: Status

    pid: int
    restarts: int
    started_at: int
    stopped_at: int

    process: str

    def __init__(self, process: str):
        self.status = Status.none

        self.pid = 0
        self.restarts = 0

        self.started_at = 0
        self.started_at = 0

        self.process = process;

    def __str__(self):
        return ", ".join("%s: %s" % i for i in vars(self).items())
    
class Process:
    autostart: bool

    restart_policy: RestartPolicy

    umask: int
    numprocs: int
    max_restarts: int
    initial_delay: int
    graceful_period: int

    cwd: str
    name: str
    exit_signal: signal.Signals
    alternative_stdout: str
    alternative_stderr: str

    cmd: list
    normal_exit_codes: list

    env: dict
    instances: list

    def __init__(self, name:str, config: dict):
        self.autostart = config.get("autostart", False)

        self.restart_policy = self._restart_policy_from_string(config.get("autorestart", "never"))

        self.umask = int(config.get("umask", "022"), 8)
        self.numprocs = config.get("numprocs", 1)
        self.max_restarts = config.get("startretries", 0)
        self.initial_delay = config.get("startsecs", 0)
        self.graceful_period = config.get("stopwaitsecs", 0)

        self.cwd = config.get("workingdir", None)
        self.name = name
        self.exit_signal = getattr(signal, config.get("stopsignal", "SIGTERM"))
        self.alternative_stdout = config.get("stdout", None)
        self.alternative_stderr = config.get("stderr", None)

        self.cmd = config.get("command").split()
        self.normal_exit_codes = config.get("exitcodes", [0])

        self.env = config["environment"]

        self.instances = [ProcessInstance(self.name) for i in range(self.numprocs)]

    def _restart_policy_from_string(self, string):
        for i in RestartPolicy:
            if i.name == string:
                return i

        return None

    def __str__(self):
        return "\n".join("%s: %s" % (k, str([str(i) for i in v]) if isinstance(v, list) else v) for (k, v) in vars(self).items())

class Runner:
    """
    Runner is a core entity which runs/stops/monitors required programs
    """
    _processes: dict # Program as a whole
    _instances: dict # Singular instance of a program
    _config: dict # Current configuration on which the runner relies as source of truth

    def __init__(self):
        self._processes = dict()
        self._instances = dict()
        self._config = dict()

        signal.signal(signal.SIGCHLD, lambda s, f: self._children_signal_handler(s ,f))

    # Will trigger config reload, checking new/old/changed programs and act accordingly
    def reload(self, config: dict):
        """
        This method will trigger configuration reload
        Old programs will be stopped then deleted
        New programs will be added as usual
        Changed programs will be stopped and then started again with new configuration
        """
        old_set_of_keys = set(self._config.keys())
        new_set_of_keys = set(config.keys())

        keys_to_delete = old_set_of_keys - new_set_of_keys
        keys_to_add = new_set_of_keys - old_set_of_keys

        for i in keys_to_delete:
            # Mark the program as deleted, after it's finished - remove it
            pass

        for i in keys_to_add:
            # Create new Process per key
            pass

        unchanged_keys = old_set_of_keys & new_set_of_keys

        for i in unchanged_keys:
            if self._config[i] != config[i]:
                # Mark the process as changed, after it's finished - run it with new configuration
                pass

    def pid(self, name: str) -> list:
        """
        Returns pid of requested program
        If not name is provided - returns runner pid
        If no such program exist in runner state - returns None
        """
        if name == None:
            return [os.getpid()]

        if name not in self._processes:
            return None

        return [i.pid for i in self._processes[name].instances]

    def status(self, name: str) -> dict:
        """
        Returns current status of the program
        The returned dict contains the process and its instances
        """
        pass

    def restart(self, name: str):
        """
        Restarts requested program by stopping it first then running again
        If name is None - restarts all programs
        """
        pass

    def start(self, name: str):
        """
        Attempts to start requested program if it's not already running
        If name is None - starts all processes that are not running already
        """
        pass

    def stop(self, name: str):
        """
        Attempts to stop requested program, if it's not already stopped
        If the name is None - tries to stop ALL the programs
        """
        pass

    def update(self):
        """
        This method is intended to be called outside of runner
        The purpose of this method is to track timing events such start/stop delays
        To save CPU cycles - best to call it once per sec using time.sleep
        """
        pass

    def _children_signal_handler(self, signum, frame):
        """
        This is a callback which will be called each time the child process finishes
        The reason will be interpreted based on configuration and received return value
        Could be normal stop or failed/unexpected exit due to various reasons
        """
        try:
            pid, exit_code = os.waitpid(-1, os.WNOHANG)

            while pid > 0:
                instance: ProcessInstance = self._instances[pid]
                process: Process = self._processes[instance.process]

                if exit_code in self._processes[p.process].normal_exit_codes:
                    p.status = process.Status.stopped
                else:
                    p.status = process.Status.failed
                
                pid, exit_code = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            pass

    def _run_process(self, g: process.ProcessGroup, p: process.Process):
        """
        """
        if p.status != process.Status.none:
            p.restarts += 1

            del self.processes[p.pid]

        p.status = process.Status.starting

        pid = os.fork()

        if pid == 0:
            sys.stdout = open(g.alternative_stdout)
            sys.stderr = open(g.alternative_stderr)

            os.chdir(g.cwd)

            os.umask(g.umask)

            signal.signal(getattr(signal, g.exit_signal), lambda s, f: sys.exit(g.normal_exit_codes[0]))

            os.execvpe(g.cmd[0], g.cmd, g.env)
        else:
            p.pid = pid
            p.started_at = int(time.time())

            self.processes[pid] = p;

    def _sync_state(self):
        for g in self.process_groups.values():
            for p in g.processes:
                if p.restarts >= g.restarts:
                    continue

                if p.status == process.Status.starting and time.time() - p.started_at > g.initial_delay:
                    p.status = process.Status.running

                if p.status == process.Status.none and g.autostart == True:
                    self._run_process(g, p)
                elif p.status == process.Status.stopped and g.restart_policy == process.RestartPolicy.always:
                    self._run_process(g, p)
                elif p.status == process.Status.failed and g.restart_policy == process.RestartPolicy.on_failure:
                    self._run_process(g, p)
                else:
                    pass

if __name__ == "__main__":
    runner = Runner()

    config = parser.create_parser().parse()["programs"]

    runner.config = config

# def move_cursor_up_and_clear(n=1):
#     for _ in range(n):
#         print("\033[K", end='')
#         print(f"\033[1A", end='')
