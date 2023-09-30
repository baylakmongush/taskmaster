import socket
import os
import parser_config

# Запустите этот серверный код следующим образом:
# python taskmasterserver.py
#
# По умолчанию, из файла taskmaster_socket будет создан UNIX domain socket.


class TaskMasterCtlServer:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
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
        self.should_exit = False

    def start(self):
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)
        print(f"Server listen to socket: {self.socket_path}")

    def handle_client(self, client_socket):
        while True:
            command = client_socket.recv(1024).decode()
            if not command:
                break

            parts = command.split()
            if len(parts) == 0:
                continue

            action = parts[0]
            args = parts[1:]

            if action == "start":
                if args:
                    task_name = " ".join(args)
                    self.start_task(client_socket, task_name)
                else:
                    self.send_command_help(client_socket, "start")
            elif action == "stop":
                if args:
                    task_name = " ".join(args)
                    self.stop_task(client_socket, task_name)
                else:
                    self.send_command_help(client_socket, "stop")
            elif action == "status":
                if args:
                    task_name = " ".join(args)
                    self.get_status_task(client_socket, task_name)
                else:
                    status_info = self.get_all_program_status()
                    client_socket.send(status_info.encode())
            elif action == "reread":
                self.reread(client_socket)
            elif action == "reload":
                if args:
                    task_name = " ".join(args)
                    self.reload_task(client_socket, task_name)
                else:
                    self.send_command_help(client_socket, "reload")
            elif action == "quit":
                break
            elif action == "exit":
                break
            elif action == "config":
                if args:
                    config_str = " ".join(args)
                    config_data = parser_config.deserialize_config(config_str)
                    self.update_config(config_data, client_socket)
                else:
                    self.send_command_help(client_socket, "config")
            elif action == "help":
                if args:
                    cmd_to_help = args[0]
                    self.send_command_help(client_socket, cmd_to_help)
                else:
                    self.send_help_info(client_socket)
            elif action == "version":
                response = "1.0\n"
                client_socket.send(response.encode())
            else:
                response = f"*** Unknown syntax: {command}\n"
                client_socket.send(response.encode())

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

    def run(self):
        self.start()
        try:
            while not self.should_exit:
                client_socket, _ = self.server_socket.accept()
                self.handle_client(client_socket)
                client_socket.close()
        except KeyboardInterrupt:
            print("Ctrl+C pressed...")
            self.shutdown_server()
        except EOFError:
            print("Ctrl+D pressed...")
            self.shutdown_server()

    def shutdown_server(self):
        # Закрыть серверный сокет и завершить выполнение
        self.server_socket.close()
        self.should_exit = True


if __name__ == "__main__":
    socket_path = "./taskmaster_socket"  # Путь к UNIX domain socket
    server = TaskMasterCtlServer(socket_path)
    server.run()