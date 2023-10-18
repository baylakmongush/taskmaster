import socket
import readline
import parser_config
import argparse
import sys
from serialization import serialize_config


# Запустите этот клиентский код следующим образом:
# По умолчанию, taskmaster_socket находится в текущей директории.
# Если вы хотите изменить путь к taskmaster_socket, то измените его в taskmasterserver.py и taskmasterclient.py
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

    def connect(self):
        try:
            self.client_socket.connect(self.socket_path)
            return True
        except Exception as e:
            return False

    def send_command(self, command):
        try:
            self.client_socket.send(command.encode())
            response = self.client_socket.recv(1024).decode()
            print(response)
        except BrokenPipeError:
            print("Server connection closed...")
            sys.exit(0)

    def send_config(self, config_data):
        config_str = serialize_config(config_data)
        try:
            self.client_socket.send(f"config {config_str}".encode())
            response = self.client_socket.recv(1024).decode()
            print(response)
        except BrokenPipeError:
            print("Server connection closed...")
            sys.exit(0)

    def close(self):
        self.client_socket.close()


def main():
    socket_path = "./taskmaster_socket"  # Путь к UNIX domain socket
    client = TaskMasterCtlClient(socket_path)

    if not client.connect():
        print("Error: Server is not running.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="TaskMasterCtl client")
    parser.add_argument("command", nargs="*", help="Command to send")
    parser.add_argument("-c", "--config", type=str, help="Path to the configuration file")

    args = parser.parse_args()

    config_path = args.config
    config_parser = parser_config.Parser()

    if config_path is not None:
        config_parser.parse_from_file(config_path)

    config_data = config_parser.get_config_data()
    client.send_config(config_data)

    if args.command:
        command = " ".join(args.command)
        client.send_command(command)
    else:
        while True:
            try:
                user_input = input("taskmaster> ").strip()
                if user_input.lower() in ["quit", "exit"]:
                    break
                if user_input:
                    client.send_command(user_input)
            except KeyboardInterrupt:
                print("Ctrl+C pressed...")
                break
            except EOFError:
                print("Ctrl+D pressed...")
                break

    client.close()


if __name__ == "__main__":
    main()