

class CommandHandler:

    def __init__(self, logging, runner):

        self.runner = runner
        self.available_commands = [
            "add", "exit", "open", "reload", "restart",
            "start", "tail", "avail", "fg", "pid",
            "remove", "shutdown", "status", "update",
            "clear", "maintail", "quit",
            "signal", "stop", "version"
        ]
        self.command_help = {
            "start": "start <name>\tStart a single process\nstart <gname>:*\t\tStart all processes in a group\nstart <name> <name>\tStart multiple processes or groups\nstart all\t\tStart all processes",
            "stop": "stop <name>\tStop a single process\nstop <gname>:*\t\tStop all processes in a group\nstop <name> <name>\tStop multiple processes or groups\nstop all\t\tStop all processes",
            "status": "status <name>\tGet status for a single process\nstatus <gname>:*\tGet status for all processes in a group\nstatus <name> <name>\tGet status for multiple named processes\nstatus\t\t\tGet all process status info",
            "restart": "restart\t\tRestart the remote taskmasterd",
            "help": "help\t\tPrint a list of available actions\nhelp <action>\t\tPrint help for <action>",
            "quit": "quit\t\tExit the taskmasterd shell.",
            "exit": "exit\t\tExit the taskmasterd shell.",
            "version": "version\t\tShow the version of the remote taskmasterd process"
        }
        self.program_status = {}

    def start_task(self, client_socket, task_name, logging):
        result = self.runner.start(task_name)
        if result:
            response = f"{task_name}: started\n"
        else:
            response = f"{task_name}: not started\n"
        client_socket.send(response.encode())

    def stop_task(self, client_socket, task_name, logging):
        result = self.runner.stop(task_name)
        if result:
            response = f"{task_name}: stopped\n"
        else:
            response = f"{task_name}: not stopped\n"
        client_socket.send(response.encode())

    def restart_task(self, client_socket, task_name, logging):
        result = self.runner.restart(task_name)
        if result:
            response = f"{task_name}: restarted\n"
        else:
            response = f"{task_name}: not restarted\n"
        client_socket.send(response.encode())

    def get_pid(self, client_socket, task_name, logging):
        result = self.runner.pid(task_name)
        if result:
            response = str(result) + "\n"
        else:
            response = f"{task_name} UNKNOWN\n"
        client_socket.send(response.encode())

    def get_all_program_status(self, client_socket, logging):
        status_info = "\n".join([f"{name}\t{status}" for name, status in self.program_status.items()])
        return status_info

    def get_status_task(self, client_socket, task_name, logging):
        # Здесь код для проверки статуса задачи.
        status_info = task_name  # self.check_task_status(task_name) # информация о статусе

        if status_info is not None:
            response = self.runner.status(status_info)
            status_string = str(response)

        else:
            status_string = f"{task_name} UNKNOWN\n"

        client_socket.send(status_string.encode())

    def update_config(self, config_data, client_socket, logging):
        response = "Updated server configuration\n"
        client_socket.send(response.encode())

    def send_help_info(self, client_socket, logging):
        help_info = "default commands (type help <topic>):\n"
        help_info += "=====================================\n"
        help_info += " ".join(self.available_commands) + "\n"
        client_socket.send(help_info.encode())

    def send_command_help(self, client_socket, command, logging):
        if command in self.command_help:
            help_info = f"{command}: {self.command_help[command]}\n"
            client_socket.send(help_info.encode())
        else:
            response = f"Help information not available for command: {command}\n"
            client_socket.send(response.encode())

    def update_program_status(self, program_name, status, logging):
        self.program_status[program_name] = status
