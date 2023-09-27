import socket
import os

# Запустите этот серверный код следующим образом:
# python taskmasterserver.py
#
# По умолчанию, сервер будет слушать localhost:8080.
# Вы можете настроить хост и порт, установив соответствующие переменные окружения:
# export TASKMASTERCTL_HOST=ваш_хост
# export TASKMASTERCTL_PORT=ваш_порт
# Затем запустите серверный код.


class TaskMasterCtlServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Server listen to {self.host}:{self.port}")

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
                self.get_status(client_socket, task_name)
            elif command == "reread":
                self.reread(client_socket)
            elif command.startswith("reload "):
                task_name = command[len("reload "):]
                self.reload_task(client_socket, task_name)
            elif command == "quit":
                break
            else:
                response = f"Unknown command: {command}\n"
                client_socket.send(response.encode())

    def start_task(self, client_socket, task_name):
        # Здесь код для запуска задачи.
        response = f"Starting task: {task_name}\n"
        client_socket.send(response.encode())

    def stop_task(self, client_socket, task_name):
        # Здесь код для остановки задачи.
        response = f"Stopping task: {task_name}\n"
        client_socket.send(response.encode())

    def get_status(self, client_socket, task_name):
        # Здесь код для проверки статуса задачи.
        response = f"Task status: {task_name}\n"
        client_socket.send(response.encode())

    def reread(self, client_socket):
        # Здесь код для выполнения команды reread.
        response = "Executing the reread command\n"
        client_socket.send(response.encode())

    def reload_task(self, client_socket, task_name):
        # Здесь код для перезапуска задачи.
        response = f"Reloading task: {task_name}\n"
        client_socket.send(response.encode())

    def run(self):
        self.start()
        while True:
            client_socket, _ = self.server_socket.accept()
            self.handle_client(client_socket)
            client_socket.close()


if __name__ == "__main__":
    host = os.getenv("TASKMASTERCTL_HOST", "localhost")
    port = int(os.getenv("TASKMASTERCTL_PORT", "8080"))

    server = TaskMasterCtlServer(host, port)
    server.run()
