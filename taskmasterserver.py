import socket
import os
import parser_config

# Запустите этот серверный код следующим образом:
# python taskmasterserver.py
#
# По умолчанию, сервер будет слушать localhost:8080.
# Вы можете настроить хост и порт, установив соответствующие переменные окружения:
# export TASKMASTERCTL_HOST=ваш_хост
# export TASKMASTERCTL_PORT=ваш_порт
# Затем запустите серверный код.


class TaskMasterCtlServer:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

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

            if command.startswith("start "):
                task_name = command[len("start "):]
                self.start_task(client_socket, task_name)
            elif command.startswith("stop "):
                task_name = command[len("stop "):]
                self.stop_task(client_socket, task_name)
            elif command.startswith("status "):
                task_name = command[len("status "):]
                self.status_task(client_socket, task_name)
            elif command == "reread":
                self.reread(client_socket)
            elif command.startswith("reload "):
                task_name = command[len("reload "):]
                self.reload_task(client_socket, task_name)
            elif command == "quit":
                break
            elif command.startswith("config "):
                config_str = command[len("config "):]
                config_data = parser_config.deserialize_config(config_str)
                self.update_config(config_data, client_socket)
            else:
                response = f"Unknown command: {command}\n"
                client_socket.send(response.encode())

    def start_task(self, client_socket, task_name):
        # Здесь код для запуска задачи.
        response = f"{task_name}: started\n"
        client_socket.send(response.encode())

    def stop_task(self, client_socket, task_name):
        # Здесь код для остановки задачи.
        response = f"{task_name}: stopped\n"
        client_socket.send(response.encode())

    def status_task(self, client_socket, task_name):
        # Здесь код для проверки статуса задачи.
        status_info = self.check_task_status(task_name) # информация о статусе

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

    def run(self):
        self.start()
        while True:
            client_socket, _ = self.server_socket.accept()
            self.handle_client(client_socket)
            client_socket.close()


if __name__ == "__main__":
    socket_path = "./taskmaster_socket"  # Путь к UNIX domain socket
    server = TaskMasterCtlServer(socket_path)
    server.run()