import socket
import os
from serialization import deserialize_config
from command_handler import CommandHandler
import logging


# Запустите этот серверный код следующим образом:
# python taskmasterserver.py
#
# По умолчанию, из файла taskmaster_socket будет создан UNIX domain socket.


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='server.log'
)


class TaskMasterCtlServer:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.should_exit = False

    def start(self):
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)
        logging.info(f"Server listen to socket: {self.socket_path}")

    def handle_client(self, client_socket):
        command_handler = CommandHandler()
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
                    command_handler.start_task(client_socket, task_name)
                else:
                    command_handler.send_command_help(client_socket, "start")
            elif action == "stop":
                if args:
                    task_name = " ".join(args)
                    command_handler.stop_task(client_socket, task_name)
                else:
                    command_handler.send_command_help(client_socket, "stop")
            elif action == "status":
                if args:
                    task_name = " ".join(args)
                    command_handler.get_status_task(client_socket, task_name)
                else:
                    status_info = command_handler.get_all_program_status()
                    client_socket.send(status_info.encode())
            elif action == "reread":
                command_handler.reread(client_socket)
            elif action == "reload":
                if args:
                    task_name = " ".join(args)
                    command_handler.reload_task(client_socket, task_name)
                else:
                    command_handler.send_command_help(client_socket, "reload")
            elif action == "quit":
                break
            elif action == "exit":
                break
            elif action == "config":
                if args:
                    config_str = " ".join(args)
                    config_data = deserialize_config(config_str)
                    command_handler.update_config(config_data, client_socket)
                else:
                    command_handler.send_command_help(client_socket, "config")
            elif action == "help":
                if args:
                    cmd_to_help = args[0]
                    command_handler.send_command_help(client_socket, cmd_to_help)
                else:
                    command_handler.send_help_info(client_socket)
            elif action == "version":
                response = "1.0\n"
                client_socket.send(response.encode())
            else:
                response = f"*** Unknown syntax: {command}\n"
                client_socket.send(response.encode())

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
        self.server_socket.close()
        self.should_exit = True


if __name__ == "__main__":
    socket_path = "./taskmaster_socket"  # Путь к UNIX domain socket
    server = TaskMasterCtlServer(socket_path)
    server.run()
