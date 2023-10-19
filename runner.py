import os
import sys
import time
import enum
import signal
import logging
import tempfile
import threading

import parser



class ProcessInstanceStatus(enum.Enum):
    created = 0
    starting = 1
    running = 2
    stopping = 3
    stopped = 4
    failed = 5


class ProcessStatus(enum.Enum):
    created = 0
    running = 1
    stopping = 2
    reloading = 3
    stopped = 4
    deleted = 5


class RestartPolicy(enum.Enum):
    never = 0
    always = 1
    on_failure = 2


class ProcessInstance:
    status: ProcessInstanceStatus

    pid: int
    restarts: int

    process: str

    def __init__(self, process: str):
        self.status = ProcessInstanceStatus.created

        self.pid = 0
        self.restarts = 0

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
        self.status = ProcessStatus.created
        
        self.running_processes_counter = 0

        self.name = name

        self.load_config(config)

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

        self.instances = [ProcessInstance(self.name) for i in range(self.numprocs)]

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
    _logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self._processes = dict()
        self._instances = dict()
        self._config = dict()
        self._lock = threading.Lock()
        self._logger = logger

        self._setup_signal_handlers()

    # Will trigger config reload, checking new/old/changed programs and act accordingly
    def reload(self, config: dict):
        """
        This method will trigger configuration reload
        Old programs will be stopped then deleted
        New programs will be added as usual
        Changed programs will be stopped and then started again with new configuration
        """
        self._logger.info("Loading configuration file...")

        with self._lock:
            old_set_of_keys = set(self._config.keys())
            new_set_of_keys = set(config.keys())

            keys_to_delete = old_set_of_keys - new_set_of_keys
            keys_to_add = new_set_of_keys - old_set_of_keys

            for k in keys_to_delete:
                print("Deleting", k)

                self._processes[k].status = ProcessStatus.deleted

                for i in self._processes[k].instances:
                    self._stop_instance(i)

            for k in keys_to_add:
                self._processes[k] = Process(k, config[k]) 

                self._processes[k].status = ProcessStatus.running

                for i in self._processes[k].instances:
                    self._run_instance(i)

            unchanged_keys = old_set_of_keys & new_set_of_keys

            for i in unchanged_keys:
                if self._config[i] != config[i]:
                    self._processes[i].status = ProcessStatus.reloading

                    for j in self._processes[i].instances:
                        self._stop_instance(j)

            self._config = config  

    def start(self, name: str) -> bool:
        """
        Attempts to start requested program if it's not already running
        If name is None - starts all processes that are not running already
        """
        with self._lock:
            if name == None:
                return False

            if name not in self._processes:
                return False

            process: Process = self._processes[name]

            if process.status != ProcessStatus.stopped:
                return False

            process.status = ProcessStatus.running

            for i in self._processes[name].instances:
                self._run_instance(i)

            return True

    def stop(self, name: str) -> bool:
        """
        Attempts to stop requested program, if it's not already stopped
        If the name is None - tries to stop ALL the programs
        """
        with self._lock:
            if name == None:
                return False

            if name not in self._processes:
                return False

            process: Process = self._processes[name]

            if process.status != ProcessStatus.running:
                return False

            process.status = ProcessStatus.stopping

            for i in self._processes[name].instances:
                self._stop_instance(i)

            return True

    def restart(self, name: str):
        """
        Restarts requested program by stopping it first then running again
        If name is None - restarts all programs
        """
        with self._lock:
            if name == None:
                return False

            if name not in self._processes:
                return False

            process: Process = self._processes[name]

            if process.status == ProcessStatus.running:
                process.status = ProcessStatus.reloading

                for i in self._processes[name].instances:
                    self._stop_instance(i)
            elif process.status == ProcessStatus.stopped:
                process.status = ProcessStatus.running

                for i in self._processes[name].instances:
                    self._run_instance(i)
            else:
                return False

            return True

    def status(self, name: str) -> dict:
        """
        Returns current status of the program
        If name is None - returns status of all the programs
        If no such program exist in runner state - returns None
        See Process class to interpret the status
        """
        with self._lock:
            if name == None:
                return self._processes

            if name not in self._processes:
                return None

            return self._processes[name]

    def pid(self, name: str) -> list:
        """
        Returns pid of requested program
        If no name is provided - returns runner pid
        If no such program exist in runner state - returns None
        """
        with self._lock:
            if name == None:
                return [os.getpid()]

            if name not in self._processes:
                return None

            return [i.pid for i in self._processes[name].instances]

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGCHLD, lambda s, f: self._children_signal_handler(s ,f))
        #signal.signal(signal.SIGHUP, lambda s, f: self._

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
                        instance.status = ProcessInstanceStatus.stopped

                        if process.status == ProcessStatus.running and process.restart_policy == RestartPolicy.always:
                            self._run_instance(instance) if instance.restarts < process.max_restarts else None
                        elif process.status == ProcessStatus.stopping and process.running_processes_counter == 0:
                            process.status = ProcessStatus.stopped
                    else:
                        instance.status = ProcessInstanceStatus.failed

                        if process.status == ProcessStatus.running and process.restart_policy == RestartPolicy.on_failure:
                            self._run_instance(instance) if instance.restarts < process.max_restarts else None
                        elif process.status == ProcessStatus.stopping and process.running_processes_counter == 0:
                            process.status = ProcessStatus.stopped

                    if process.running_processes_counter == 0:
                        if process.status == ProcessStatus.reloading:
                            process.status = ProcessStatus.running

                            process.load_config(self._config[process.name])

                            for i in process.instances:
                                self._run_instance(i) 
                        elif process.status == ProcessStatus.deleted:
                            del self._processes[instance.process]
                        else:
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
            instance.status = ProcessInstanceStatus.starting if process.initial_delay > 0 else ProcessInstanceStatus.running

            instance.pid = pid
            instance.restarts += 1

            process.running_processes_counter += 1

            self._instances[pid] = instance;

            threading.Timer(process.initial_delay, lambda: self._initial_delay_handler(instance)).start()

    def _stop_instance(self, instance: ProcessInstance):
        if instance.status == ProcessInstanceStatus.starting or instance.status == ProcessInstanceStatus.running:
            process: Process = self._processes[instance.process]

            instance.status = ProcessInstanceStatus.stopping if process.graceful_period > 0 else instance.status

            instance.restarts = 0

            os.kill(instance.pid, process.exit_signal)

            threading.Timer(process.graceful_period, lambda: self._graceful_shutdown_handler(instance)).start()

    def _initial_delay_handler(self, instance: ProcessInstance):
        with self._lock:
            if instance.status == ProcessInstanceStatus.starting:
                instance.status = ProcessInstanceStatus.running

    def _graceful_shutdown_handler(self, instance: ProcessInstance):
        with self._lock:
            if instance.status == ProcessInstanceStatus.stopping:
                os.kill(i.pid, signal.SIGKILL)


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

    runner = Runner(logger)

    while True:
        command = input("Command: ")

        config = prs.parse()["programs"]

        runner.reload(config)

        if int(command.split()[0]) == 1:
            if not runner.stop(command.split()[1]):
                print("Error")
        elif int(command.split()[0]) == 2:
            if not runner.start(command.split()[1]):
                print("Error")
        elif int(command.split()[0]) == 3:
            if not runner.restart(command.split()[1]):
                print("Error")

# def move_cursor_up_and_clear(n=1):
#     for _ in range(n):
#         print("\033[K", end='')
#         print(f"\033[1A", end='')
                
# import os
# import sys
# import enum
# import signal
# import tempfile
# import threading
# import logging
# 
# from typing import List, Dict, Any
# 
# 
# class Autorestart(enum.Enum):
#     true = 0,
#     unexpected = 1,
#     false = 2,
# 
# 
# class ProcessState(enum.Enum):
#     stopped = 0, # The process has been stopped due to a stop request or has never been started
#     starting = 1, # The process is starting due to a start request
#     running = 2, # The process is running
#     backoff = 3, # The process entered the starting state but subsequently exited too quickly (before the time defined in startsecs) to move to the running state
#     stopping = 4, # The process is stopping due to a stop request
#     exited = 5, # The process exited from the RUNNING state (expectedly or unexpectedly)
#     fatal = 6, # The process could not be started successfully
#     unknown = 7 # The process is in an unknown state
# 
# 
# class Program:
#     stdout_logfile: str
#     stderr_logfile: str
#     startretries: int
#     stopwaitsecs: int
#     environment: Dict[str, str]
#     autorestart: Autorestart
#     stopsignal: signal.Signals
#     exitcodes: List[int]
#     autostart: bool
#     directory: str
#     startsecs: int
#     numprocs: int
#     command: List[str]
#     umask: int
# 
#     def __init__(self, name: str, config: Dict[str, Any]):
#         self.stdout_logfile = config.get("stdout", "AUTO") # Either AUTO, NONE or str
#         self.stderr_logfile = config.get("stderr", "AUTO") # Either AUTO, NONE or str
#         self.startretries = config.get("startretries", 3)
#         self.stopwaitsecs = config.get("stopwaitsecs", 10)
#         self.environment = config.get("environment", dict())
#         self.autorestart = config.get("autorestart", Autorestart.unexpected)
#         self.stopsignal = config.get("stopsignal", signal.Signals.SIGTERM)
#         self.exitcodes = config.get("exitcodes", [0])
#         self.autostart = config.get("autostart", True)
#         self.directory = config.get("directory", None) # None - do not chdir
#         self.startsecs = config.get("startsecs", 1)
#         self.numprocs = config.get("numprocs", 1)
#         self.command = config.get("command", None) # Must be filled - error will be thrown otherwise
#         self.umask = config.get("umask", None) # None - do not set umask
# 
#     def __str__(self):
#         return ", ".join("%s: %s" % i for i in vars(self).items())
# 
# 
# class Process:
#     restarts: int
#     group: Group
#     state: ProcessState
#     lock: threading.Lock
#     name: str
#     pid: int
# 
#     def __init__(self, group: Group, name: str, state: ProcessState, pid: int):
#         self.group = group
#         self.state = state
#         self.lock = threading.Lock()
#         self.name = name
#         self.pid = pid
# 
#     def __str__(self):
#         return ", ".join("%s: %s" % i for i in vars(self).items())
# 
# 
# class Group:
#     stdout_logfile: str
#     stderr_logfile: str
#     startretries: int
#     stopwaitsecs: int
#     environment: Dict[str, str]
#     autorestart: Autorestart
#     stopsignal: signal.Signals
#     exitcodes: List[int]
#     autostart: bool
#     directory: str
#     startsecs: int
#     numprocs: int
#     command: List[str]
#     umask: int
#     name: str
# 
#     processes: List[Process]
# 
#     def __init__(self, name: str, config: Dict[str, Any]):
#         self.stdout_logfile = config.get("stdout", "AUTO") # Either AUTO, NONE or str
#         self.stderr_logfile = config.get("stderr", "AUTO") # Either AUTO, NONE or str
#         self.startretries = config.get("startretries", 3)
#         self.stopwaitsecs = config.get("stopwaitsecs", 10)
#         self.environment = config.get("environment", dict())
#         self.autorestart = config.get("autorestart", Autorestart.unexpected)
#         self.stopsignal = config.get("stopsignal", signal.Signals.SIGTERM)
#         self.exitcodes = config.get("exitcodes", [0])
#         self.autostart = config.get("autostart", True)
#         self.directory = config.get("directory", None) # None - do not chdir
#         self.startsecs = config.get("startsecs", 1)
#         self.numprocs = config.get("numprocs", 1)
#         self.command = config.get("command", None) # Must be filled - error will be thrown otherwise
#         self.umask = config.get("umask", None) # None - do not set umask
#         self.name = name
# 
#         self.processes = [Process()]
# 
#     def __str__(self):
#         return "\n".join("%s: %s" % (k, str([str(i) for i in v]) if isinstance(v, list) else v) for (k, v) in vars(self).items())
# 
# 
# class Supervisor:
#     _processes: Dict[str, Process]
#     _groups: Dict[str, Group]
#     _config: Dict[str, Any]
#     _logger: logging.Logger
# 
#     _pid_to_process: Dict[int, Process]
#     _pid_to_group: Dict[int, Group]
# 
#     def __init__(self, logger: logging.Logger):
#         self._processes = list()
#         self._groups = dict()
#         self._config = dict()
#         self._logger = logger
#     
#     def reload_config(self, config: Dict[str, Any]):
#         self._logger.info("Updating runner configuration...")
# 
#         removed_groups = set(self._config.keys()) - set(config.keys())
#         remain_groups = set(self._config.keys()) & set(config.keys())
#         added_groups = set(config.keys()) - set(self._config.keys())
# 
#         for group in removed_groups:
#             self._logger.info(f"Group {group} has been removed")
# 
#         for group in remain_groups:
#             if self._config[group] != config[group]:
#                 self._logger.info(f"Group {group} has been changed")
# 
#         for group in added_groups:
#             self._logger.info(f"Group {group} has been added")
# 
#             self._groups[group] = Group(group, config[group])
# 
#             if not self._groups[group].autostart:
#                 continue
# 
#             for i in range(self._groups[group].numprocs):
#                 self._spawn_process(group, f"{group}{i}")
# 
#     def start(self, name: str):
#         pass
# 
#     def stop(self, name: str):
#         pass
# 
#     def status(self, name: str):
#         pass
# 
#     def restart(self, name: str):
#         pass
# 
#     def _sigchld_handler(self):
#         def _handler():
#             pass
# 
#         threading.Thread(target=_handler).start()
# 
#     def _spawn_process(self, group: Group, name: str) -> Process:
#         pid = os.fork()
# 
#         if pid == 0:
#             _redirect_fd_into_logfile(group, sys.stdout.fileno(), group.stdout_logfile, name, ".stdout")
#             _redirect_fd_into_logfile(group, sys.stderr.fileno(), group.stderr_logfile, name, ".stderr")
# 
#             try:
#                 os.chdir(group.directory)
#             except Exception:
#                 pass
# 
#             try:
#                 os.umask(group.umask)
#             except Exception:
#                 pass
# 
#             signal.signal(group.stopsignal, lambda s, f: sys.exit(group.exitcodes[0]))
# 
#             os.execvpe(group.command[0], group.command, group.environment)
#         else:
#             self._logger.info(f"spawned: '{process.name}' with pid {pid}")
# 
#             self._processes[pid] = Process(group, name, ProcessState.starting if group.startsecs > 0 else ProcessState.running, pid)
# 
#             if group.startsecs > 0:
#                 threading.Timer(group.startsecs, lambda: self._initial_delay_handler(process)).start()
# 
#             return self._processes[pid]
# 
#     def _stop_process(self, process: Process):
#         process.state = ProcessState.stopping if process.group.stopwaitsecs > 0 else ProcessState.stopped
# 
#         self._kill_process(process, process.group.stopsignal)
# 
#         if process.group.stopwaitsecs > 0:
#             threading.Timer(process.group.stopwaitsecs, lambda: self._graceful_shutdown_handler(process))
# 
#     def _redirect_fd_into_logfile(self, group: Group, fd: int, logfile: str, prefix: str = "", suffix: str = ""):
#         file = None
# 
#         if logfile == "AUTO":
#             file = tempfile.NamedTemporaryFile(mode="w", prefix=prefix, suffix=suffix, delete=False)
#         else if logfile == "NONE":
#             file = open("/dev/null", "w")
#         else:
#             try:
#                 file = open(logfile, "w")
#             except FileNotFoundError:
#                 file = open("/dev/null", "w")
#         
#         os.dup2(file.fileno(), fd)
# 
#     def _initial_delay_handler(self, process: Process):
#         if process.state == ProcessState.starting:
#             process.state = ProcessState.running
# 
#     def _graceful_shutdown_handler(self, process: Process):
#         if process.state == ProcessState.stopping:
#             self._kill_process(process, signal.Signals.SIGKILL)
# 
#     def _kill_process(self, process: Process, signal: signal.Signals):
#         try:
#             os.kill(process.pid, signal)
#         except Exception:
#             pass
