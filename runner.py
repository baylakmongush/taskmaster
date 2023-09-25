import os
import sys
import enum
import time
import parser
import process
import logging 

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

_logger = logging.getLogger(__name__)


def move_cursor_up_and_clear(n=1):
    for _ in range(n):
        print("\033[K", end='')
        print(f"\033[1A", end='')


class Runner:
    process_groups: dict
    processes: dict

    def __init__(self):
        self.process_groups = dict()
        self.processes = dict()

        config = parser.create_parser().parse()

        for k, v in config["programs"].items():
            self.process_groups[k] = process.ProcessGroup(v)

    def status(self):
        try:
            pid, exit_code = os.waitpid(-1, os.WNOHANG)

            while pid > 0:
                p = self.processes[pid]

                if exit_code in p.normal_exit_codes:
                    p.status = process.Status.stopped
                else:
                    p.status = process.Status.failed
                
                pid, exit_code = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            pass

    def sync_state(self):
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

    def update(self):
        self.status()
        self.sync_state()

        for g in self.process_groups.values():
            print(g)

        move_cursor_up_and_clear(30)

    def _run_process(self, g: process.ProcessGroup, p: process.Process):
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

            os.execvpe(g.cmd[0], g.cmd, g.env)
        else:
            p.pid = pid
            p.started_at = int(time.time())

            self.processes[pid] = p;

    def get_status(self, name = None):
        pass
    
    def reload_config(self, config):
        pass


if __name__ == "__main__":
    runner = Runner()

    while True:
        runner.update()
        time.sleep(1)

    runner.loop()

