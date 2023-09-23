import os
import sys
import enum
import time
import parser
import process


class State:
    running: bool

    process_groups: dict
    processes: dict

    def __init__(self):
        self.running = True
        self.process_groups = dict()
        self.processes = dict()


class Runner:
    state: State

    parser: parser.Parser
    data: dict

    def __init__(self):
        self.state = State()

        self.parser = parser.create_parser()

        self.data = self.parser.parse()

        for k, v in self.data["programs"].items():
            process_group = process.ProcessGroup()

            process_group.autostart = v["autostart"]
            process_group.restart_policy = self._restart_policy_from_string(v["autorestart"])
            process_group.max_numprocs = v["numprocs"]
            process_group.max_restarts = v["startretries"]
            process_group.initial_delay = v["startsecs"]
            process_group.graceful_period = v["stopwaitsecs"]
            process_group.permissions = int(v["umask"], 8)
            process_group.cwd = v["workingdir"]
            process_group.exit_signal = v["stopsignal"]
            process_group.alternative_stdout = v["stdout"]
            process_group.alternative_stderr = v["stderr"]
            process_group.cmd = v["command"].split()
            process_group.exit_codes = v["exitcodes"]
            process_group.env = v["environment"]

            self.state.process_groups[k] = process_group

            print(self.state.process_groups[k])

    def poll_status(self):
        try:
            pid, exit_code = os.waitpid(-1, os.WNOHANG)
            
            if pid > 0:
                print(f"Proccess {pid} exited with code {exit_code}")

                p = self.state.processes[pid]

                self.state.process_groups[p.owner].numprocs -= 1

                del self.state.processes[pid]
        except ChildProcessError:
            pass


    def sync_state(self):
        for k, process_group in self.state.process_groups.items():
            while process_group.numprocs < process_group.max_numprocs:
                pid = os.fork()

                if pid == 0:
                    os.umask(process_group.permissions)
                    os.chdir(process_group.cwd)
                    os.execvp(process_group.cmd[0], process_group.cmd)
                else:
                    p = process.Process()

                    p.status = process.Status.starting
                    p.pid = pid
                    p.restarts = 0
                    p.started_at = time.time()
                    p.stopped_at = None
                    p.last_exit_code = 0
                    p.owner = k

                    process_group.processes[pid] = p
                    self.state.processes[pid] = p

                process_group.numprocs += 1

    def loop(self):
        while (self.state.running):
            self.poll_status()
            self.sync_state()

            time.sleep(1)


    def _restart_policy_from_string(self, string):
        for i in process.RestartPolicy:
            if i.name == string:
                return i

        return None


if __name__ == "__main__":
    runner = Runner()

    runner.loop()

