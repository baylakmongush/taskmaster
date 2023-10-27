import os
import socket
import argparse
import sys
import readline
import yaml


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
            if response.startswith("Error:"):
                print(f"Server returned an error: {response}")
            else:
                print(response)
        except BrokenPipeError:
            print("Server connection closed...")
            sys.exit(0)

    def send_config(self, config_data):
        try:
            self.client_socket.send(f"config {config_data}".encode())
            response = self.client_socket.recv(1024).decode()
            if response.startswith("Error:"):
                print(f"Server returned an error: {response}")
            else:
                print(response)
        except BrokenPipeError:
            print("Server connection closed...")
            sys.exit(0)

    def close(self):
        self.client_socket.close()


def main():
    # Define command-line arguments
    parser = argparse.ArgumentParser(description="TaskMasterCtl client")
    parser.add_argument("socket", type=str, help="Path to the UNIX domain socket")
    parser.add_argument("command", nargs="*", help="Command to send")
    parser.add_argument("-c", "--config", type=str, help="Path to the configuration file")

    args = parser.parse_args()
    socket_path = args.socket
    client = TaskMasterCtlClient(socket_path)

    # Attempt to connect to the server
    if not client.connect():
        print("Error: Server is not running.")
        sys.exit(1)

    config_path = args.config

    if config_path and not os.path.isfile(config_path):
        print(f"Error: The specified configuration file '{config_path}' does not exist.")
        exit(1)

    if config_path:
        with open(config_path, 'r') as file:
            try:
                config = yaml.safe_load(file)
                serialize_config(config)
                client.send_config(args.config)
            except yaml.YAMLError as e:
                print(f"Ошибка при чтении конфигурационного файла: {e}")
                return None

    # Send a command if command-line arguments are provided
    if args.command:
        command = " ".join(args.command)
        client.send_command(command)
    else:
        # Interactive mode for entering commands
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