import os
import sys
import time
import enum
import signal
import tempfile
import threading

import parser


class Status(enum.Enum):
    none = 0
    starting = 1
    running = 2
    stopping = 3
    stopped = 4
    failed = 5


class ProcessStatus(enum.Enum):
    running = 0
    stopping = 1
    stopped = 2
    deleted = 3


class RestartPolicy(enum.Enum):
    never = 0
    always = 1
    on_failure = 2


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

    status: ProcessStatus
    restart_policy: RestartPolicy

    exit_signal: signal.Signals

    umask: int
    numprocs: int
    max_restarts: int
    initial_delay: int
    graceful_period: int
    running_processes_counter: int

    cwd: str
    name: str
    stdout: str
    stderr: str
    
    cmd: list
    normal_exit_codes: list

    env: dict
    instances: list

    def __init__(self, name:str, config: dict):
        self.status = ProcessStatus.running
        
        self.running_processes_counter = 0

        self.name = name

        self.load_config(config)

        self.instances = [ProcessInstance(self.name) for i in range(self.numprocs)]

    def load_config(self, config):
        self.autostart = config.get("autostart", False)

        try:
            self.restart_policy = self._restart_policy_from_string(config.get("autorestart", "never"))
        except AttributeError:
            self.restart_policy = RestartPolicy.never
        try:
            self.exit_signal = getattr(signal, config.get("stopsignal", "SIGTERM"))
        except AttributeError:
            self.exit_signal = signal.SIGTERM

        self.umask = int(config.get("umask", "777"), 8)
        self.numprocs = config.get("numprocs", 1)
        self.max_restarts = config.get("startretries", 0)
        self.initial_delay = config.get("startsecs", 0)
        self.graceful_period = config.get("stopwaitsecs", 0)

        self.cwd = config.get("workingdir", None)
        self.stdout = config.get("stdout", "/dev/null")
        self.stderr = config.get("stderr", "/dev/null")

        self.cmd = config.get("command", "").split()
        self.normal_exit_codes = config.get("exitcodes", [0])
        if len(self.normal_exit_codes) < 1:
            self.normal_exit_codes = [0]

        self.env = config.get("environment", dict())

    def _restart_policy_from_string(self, string):
        for i in RestartPolicy:
            if i.name == string:
                return i

        raise AttributeError

    def __str__(self):
        return "\n".join("%s: %s" % (k, str([str(i) for i in v]) if isinstance(v, list) else v) for (k, v) in vars(self).items())


class Runner:
    """
    Runner is a core entity which runs/stops/monitors required programs
    """
    _processes: dict # Program as a whole
    _instances: dict # Singular instance of a program
    _config: dict # Current configuration on which the runner relies as source of truth
    _lock: threading.Lock

    def __init__(self):
        self._processes = dict()
        self._instances = dict()
        self._config = dict()
        self._lock = threading.Lock()

        signal.signal(signal.SIGCHLD, lambda s, f: self._children_signal_handler(s ,f))

    # Will trigger config reload, checking new/old/changed programs and act accordingly
    def reload(self, config: dict):
        """
        This method will trigger configuration reload
        Old programs will be stopped then deleted
        New programs will be added as usual
        Changed programs will be stopped and then started again with new configuration
        """
        with self._lock:
            old_set_of_keys = set(self._config.keys())
            new_set_of_keys = set(config.keys())

            keys_to_delete = old_set_of_keys - new_set_of_keys
            keys_to_add = new_set_of_keys - old_set_of_keys

            for k in keys_to_delete:
                self._processes[k].status = ProcessStatus.deleted

                for i in self._processes[k].instances:
                    if i.status == Status.starting or i.status == Status.running:
                        i.status = Status.stopping if self._processes[name].graceful_period > 0 else i.status

                        i.stopped_at = int(time.time())

                        os.kill(i.pid, self._processes[name].exit_signal)

            for k in keys_to_add:
                self._processes[k] = Process(k, config[k]) 

                for i in self._processes[k].instances:
                    self._run_instance(i)

            self._config = config

            # unchanged_keys = old_set_of_keys & new_set_of_keys

            # for i in unchanged_keys:
            #     if self._config[i] != config[i]:
            #         pass

    def pid(self, name: str) -> list:
        """
        Returns pid of requested program
        If not name is provided - returns runner pid
        If no such program exist in runner state - returns None
        """
        with self._lock:
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
        if self._processes.get(name) is not None:
            return self._processes[name]

        return None

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
        with self._lock:
            if self._processes[name] is not None and self._processes[name].status == ProcessStatus.stopped:
                self._processes[name].status = ProcessStatus.running

                for i in self._processes[name].instances:
                    self._run_instance(i)

    def stop(self, name: str):
        """
        Attempts to stop requested program, if it's not already stopped
        If the name is None - tries to stop ALL the programs
        """
        with self._lock:
            if self._processes[name] is not None and self._processes[name].status == ProcessStatus.running:
                self._processes[name].status = ProcessStatus.stopping

                for i in self._processes[name].instances:
                    if i.status == Status.starting or i.status == Status.running:
                        i.status = Status.stopping if self._processes[name].graceful_period > 0 else i.status

                        i.stopped_at = int(time.time())

                        os.kill(i.pid, self._processes[name].exit_signal)

    def update(self):
        """
        This method is intended to be called outside of runner
        The purpose of this method is to track timing events such start/stop delays
        To save CPU cycles - best to call it once per sec using time.sleep
        """
        with self._lock:
            for i in self._instances.values():
                process: Process = self._processes[i.process]

                if i.status == Status.starting and int(time.time()) - i.started_at > process.initial_delay:
                    i.status = Status.running

                if i.status == Status.stopping and int(time.time()) - i.stopped_at > process.graceful_period:
                    os.kill(i.pid, signal.SIGKILL)

            for k, v in self._processes.items():
                if v.status == ProcessStatus.deleted and v.running_processes_counter == 0:
                    del self._processes[k]

    def _children_signal_handler(self, signum, frame):
        """
        This is a callback which will be called each time the child process finishes
        The reason will be interpreted based on configuration and received return value
        Could be normal stop or failed/unexpected exit due to various reasons
        """
        threading.Thread(target=self._children_signal_handler_job).start()

    def _children_signal_handler_job(self):
        """
        This method is essentially a signal handler intended to run in a separate thread 
        """
        with self._lock:
            try:
                pid, exit_code = os.waitpid(-1, os.WNOHANG)

                while pid > 0:
                    instance: ProcessInstance = self._instances[pid]
                    process: Process = self._processes[instance.process]

                    process.running_processes_counter -= 1

                    del self._instances[pid]

                    if exit_code in process.normal_exit_codes:
                        instance.status = Status.stopped

                        if process.status == ProcessStatus.running and process.restart_policy == RestartPolicy.always:
                            self._run_instance(instance) if instance.restarts < process.max_restarts else None
                        elif process.status == ProcessStatus.stopping or process.running_processes_counter == 0:
                            process.status = ProcessStatus.stopped
                    else:
                        instance.status = Status.failed

                        if process.status == ProcessStatus.running and process.restart_policy == RestartPolicy.on_failure:
                            self._run_instance(instance) if instance.restarts < process.max_restarts else None
                        elif process.status == ProcessStatus.stopping or process.running_processes_counter == 0:
                            process.status = ProcessStatus.stopped

                    pid, exit_code = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                pass

    def _run_instance(self, instance: ProcessInstance):
        """
        Runs the process instance as separate process using fork and exec 
        """
        process: Process = self._processes[instance.process]

        pid = os.fork()

        if pid == 0:
            try:
                os.chdir(process.cwd)
            except Exception:
                os.chidir(tempfile.mkdtemp())

            try:
                with open(process.stdout, "w") as file:
                    os.dup2(file.fileno(), sys.stdout.fileno())
                with open(process.stderr, "w") as file:
                    os.dup2(file.fileno(), sys.stderr.fileno())
            except Exception:
                with open("/dev/null", "w") as file:
                    os.dup2(file.fileno(), sys.stdout.fileno())
                    os.dup2(file.fileno(), sys.stderr.fileno())

            try:
                os.umask(process.umask)
            except Exception:
                os.umask(0o777)

            signal.signal(process.exit_signal, lambda s, f: sys.exit(process.normal_exit_codes[0]))

            try:
                os.execvpe(process.cmd[0], process.cmd, process.env)
            except (IndexError, FileNotFoundError):
                pass
        else:
            instance.status = Status.starting if process.initial_delay > 0 else Status.running
            instance.pid = pid
            instance.restarts += 1
            instance.started_at = int(time.time())

            process.running_processes_counter += 1

            self._instances[pid] = instance;


if __name__ == "__main__":
    prs = parser.create_parser()

    runner = Runner()

    while True:
        command = input("Command: ")

        config = prs.parse()["programs"]

        runner.reload(config)

        runner.update()

        if int(command.split()[0]) == 1:
            runner.stop(command.split()[1])
        elif int(command.split()[0]) == 2:
            runner.start(command.split()[1])

# def move_cursor_up_and_clear(n=1):
#     for _ in range(n):
#         print("\033[K", end='')
#         print(f"\033[1A", end='')
