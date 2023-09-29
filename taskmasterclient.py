import os
import socket
import parser_config
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
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client_socket.connect(self.socket_path)

    def send_command(self, command):
        self.client_socket.send(command.encode())
        response = self.client_socket.recv(1024).decode()
        print(response)

    def send_config(self, config_data):
        config_str = parser_config.serialize_config(config_data)
        self.client_socket.send(f"config {config_str}".encode())
        response = self.client_socket.recv(1024).decode()
        print(response)

    def close(self):
        self.client_socket.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="TaskMasterCtl client")
    parser.add_argument("command", nargs="+", help="Command to send")
    parser.add_argument("-c", "--config", type=str, help="Path to the configuration file")

    args = parser.parse_args()

    config_path = args.config
    config_parser = parser_config.Parser()

    socket_path = "./taskmaster_socket"  # Путь к UNIX domain socket
    client = TaskMasterCtlClient(socket_path)

    if config_path is not None:
        config_parser.parse_from_file(config_path)
    else:
        config_parser.parse_from_default_paths()

    config_data = config_parser.get_config_data()
    client.send_config(config_data)
    print(config_data)

    if not args.command:
        while True:
            user_input = input("(taskmaster) ").strip()
            if user_input == "quit":
                break
            client.send_command(user_input)
    else:
        command = " ".join(args.command)
        client.send_command(command)

    client.close()
