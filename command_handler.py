

class CommandHandler:

    def __init__(self, logging, runner):

        self.runner = runner
        self.available_commands = [
            "exit", "reload", "restart",
            "start", "pid", "status",
            "quit", "stop", "version",
            "help"
        ]
        self.command_help = {
            "start": "start <name>\tStart a single process\nstart <gname>:*\t\tStart all processes in a group\nstart <name> <name>\tStart multiple processes or groups\nstart all\t\tStart all processes",
            "stop": "stop <name>\tStop a single process\nstop <gname>:*\t\tStop all processes in a group\nstop <name> <name>\tStop multiple processes or groups\nstop all\t\tStop all processes",
            "status": "status <name>\tGet status for a single process\nstatus <gname>:*\tGet status for all processes in a group\nstatus <name> <name>\tGet status for multiple named processes\nstatus\t\t\tGet all process status info",
            "restart": "restart\t\tRestart the remote taskmasterd",
            "reload": "reload\t\tReload configuration file",
            "help": "help\t\tPrint a list of available actions\nhelp <action>\t\tPrint help for <action>",
            "quit": "quit\t\tExit the taskmasterd shell.",
            "exit": "exit\t\tExit the taskmasterd shell.",
            "version": "version\t\tShow the version of the remote taskmasterd process",
            "pid": "pid <name>\tGet pid for a single process\npid <gname>:*\t\tGet pid for all processes in a group\npid <name> <name>\tGet pid for multiple named processes\npid\t\t\tGet all process pid info"
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

    def get_status(self, client_socket, task_name, logging):
        # Здесь код для проверки статуса задачи.
        status_info = task_name  # self.check_task_status(task_name) # информация о статусе

        response = self.runner.status(status_info)
        status_string = str(response)

        client_socket.send(status_string.encode())

    def reload(self, config_data, client_socket, logging):
        self.runner.reload(config_data)
        response = "Configuration updated\n"
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
