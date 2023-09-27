import os
import socket
import argparse

# Запустите этот клиентский код следующим образом:
# По умолчанию, сервер будет слушать localhost:8080.
# Вы можете настроить хост и порт, установив соответствующие переменные окружения:
# export TASKMASTERCTL_HOST=ваш_хост
# export TASKMASTERCTL_PORT=ваш_порт
# Затем запустите клиентский код с командой.
#
# python taskmasterclient.py [команда] [название задачи]
# Команды: start, stop, status, reread, reload, quit
#
# Либо:
# python taskmasterclient.py, чтобы запустить интерактивный режим.
#
# В интерактивном режиме вы можете вводить команды в формате:
# [команда] [название задачи]
# Команды: start, stop, status, reread, reload, quit


class TaskMasterCtlClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))

    def send_command(self, command):
        self.client_socket.send(command.encode())
        response = self.client_socket.recv(1024).decode()
        print(response)

    def close(self):
        self.client_socket.close()


def get_env_variables():
    host = os.getenv("TASKMASTERCTL_HOST", "localhost")
    port = int(os.getenv("TASKMASTERCTL_PORT", "8080"))
    return host, port


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TaskMasterCtl client")
    parser.add_argument("command", nargs=argparse.REMAINDER, default=["interactive"], help="Command to send (default is 'interactive')")
    args = parser.parse_args()

    host, port = get_env_variables()

    client = TaskMasterCtlClient(host, port)

    if args.command[0].lower() == "interactive":
        while True:
            user_input = input("(taskmasterctl) ").strip()
            if user_input == "quit":
                break
            client.send_command(user_input)
    else:
        command = " ".join(args.command)
        client.send_command(command)

    client.close()
