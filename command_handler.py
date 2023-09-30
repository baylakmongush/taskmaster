class CommandHandler:

    def __init__(self):
        self.available_commands = [
            "add", "exit", "open", "reload", "restart",
            "start", "tail", "avail", "fg", "pid",
            "remove", "shutdown", "status", "update",
            "clear", "maintail", "quit", "reread",
            "signal", "stop", "version"
        ]
        self.command_help = {
            "start": "start <name>\tStart a single process\nstart <gname>:*\t\tStart all processes in a group\nstart <name> <name>\tStart multiple processes or groups\nstart all\t\tStart all processes",
            "stop": "stop <name>\tStop a single process\nstop <gname>:*\t\tStop all processes in a group\nstop <name> <name>\tStop multiple processes or groups\nstop all\t\tStop all processes",
            "status": "status <name>\tGet status for a single process\nstatus <gname>:*\tGet status for all processes in a group\nstatus <name> <name>\tGet status for multiple named processes\nstatus\t\t\tGet all process status info",
            "reread": "reread\t\tReload the daemon's configuration files without add/remove",
            "reload": "reload\t\tRestart the remote taskmasterd",
            "help": "help\t\tPrint a list of available actions\nhelp <action>\t\tPrint help for <action>",
            "quit": "quit\t\tExit the taskmasterd shell.",
            "exit": "exit\t\tExit the taskmasterd shell.",
            "version": "version\t\tShow the version of the remote taskmasterd process"
        }
        self.program_status = {}

    def start_task(self, client_socket, task_name):
        # Здесь код для запуска задачи.
        self.update_program_status(task_name, "STARTED")
        response = f"{task_name}: started\n"
        client_socket.send(response.encode())

    def stop_task(self, client_socket, task_name):
        # Здесь код для остановки задачи.
        self.update_program_status(task_name, "STOPPED")
        response = f"{task_name}: stopped\n"
        client_socket.send(response.encode())

    def get_all_program_status(self):
        status_info = "\n".join([f"{name}\t{status}" for name, status in self.program_status.items()])
        return status_info

    def get_status_task(self, client_socket, task_name):
        # Здесь код для проверки статуса задачи.
        status_info = task_name #self.check_task_status(task_name) # информация о статусе

        if status_info is not None:
            response = f"{task_name} {status_info}\n"
        else:
            response = f"{task_name} UNKNOWN\n"

        client_socket.send(response.encode())

    def reread(self, client_socket):
        # Здесь код для выполнения команды reread.
        response = "Executing the reread command\n"
        client_socket.send(response.encode())

    def reload_task(self, client_socket, task_name):
        # Здесь код для перезапуска задачи.
        response = f"Reloading task: {task_name}\n"
        client_socket.send(response.encode())

    def update_config(self, config_data, client_socket):
        response = "Updated server configuration\n"
        client_socket.send(response.encode())

    def send_help_info(self, client_socket):
        help_info = "default commands (type help <topic>):\n"
        help_info += "=====================================\n"
        help_info += " ".join(self.available_commands) + "\n"
        client_socket.send(help_info.encode())

    def send_command_help(self, client_socket, command):
        if command in self.command_help:
            help_info = f"{command}: {self.command_help[command]}\n"
            client_socket.send(help_info.encode())
        else:
            response = f"Help information not available for command: {command}\n"
            client_socket.send(response.encode())

    def update_program_status(self, program_name, status):
        self.program_status[program_name] = status