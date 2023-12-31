import argparse
import select
import socket
import os
import time
import yaml
from command_handler import CommandHandler
import logging
import parser_config as config_parser
from taskmaster import Taskmaster
import signal


class TaskMasterCtlServer:
    def __init__(self, socket_path, taskmaster, config, logger):
        self.socket_path = socket_path
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.should_exit = False
        self.taskmaster = taskmaster
        self.client_sockets = []
        self.config = config
        self.config_path = None
        self.logger = logger

    def start(self):
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGQUIT, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)
        # signal.signal(signal.SIGUSR2, self.handle_signal)
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)

    def handle_client(self, client_socket):
        command_handler = CommandHandler(self.taskmaster, self.logger)
        while not self.should_exit:
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
                    if ":" in task_name:
                        group_name, process_name = task_name.split(":")
                        if group_name is not None:
                            command_handler.start_task(client_socket, group_name, process_name)
                        else:
                            response = "Error: Group name is missing.\n"
                            client_socket.send(response.encode())
                    else:
                        response = "Error: Command should be in the format 'start group_name:process_name'\n"
                        client_socket.send(response.encode())
                else:
                    command_handler.send_command_help(client_socket, "start")
            elif action == "stop":
                if args:
                    task_name = " ".join(args)
                    if ":" in task_name:
                        group_name, process_name = task_name.split(":")
                        if group_name is not None:
                            command_handler.stop_task(client_socket, group_name, process_name)
                        else:
                            response = "Error: Group name is missing.\n"
                            client_socket.send(response.encode())
                    else:
                        response = "Error: Command should be in the format 'stop group_name:process_name'\n"
                        client_socket.send(response.encode())
                else:
                    command_handler.send_command_help(client_socket, "stop")
            elif action == "status":
                if args:
                    task_name = " ".join(args)
                    if ":" in task_name:
                        group_name, process_name = task_name.split(":")
                        if group_name is not None:
                            command_handler.get_status(client_socket, group_name, process_name)
                        else:
                            response = "Error: Group name is missing.\n"
                            client_socket.send(response.encode())
                    else:
                        response = "Error: Command should be in the format 'status group_name:process_name'\n" \
                                   "Or 'status group_name:'\n"
                        client_socket.send(response.encode())
                else:
                    response = "Error: Command should be in the format 'status group_name:process_name'\n" \
                                   "Or 'status group_name:'\n"
                    client_socket.send(response.encode())
            elif action == "restart":
                if args:
                    task_name = " ".join(args)
                    group_name, process_name = task_name.split(":")
                    command_handler.restart_task(client_socket, group_name, process_name)
                else:
                    command_handler.send_command_help(client_socket, "restart")
            elif action == "pid":
                if args:
                    task_name = " ".join(args)
                    group_name, process_name = task_name.split(":")
                    command_handler.get_pid(client_socket, group_name, process_name)
                else:
                    command_handler.send_command_help(client_socket, "pid")
            elif action in ("quit", "exit"):
                break
            elif action == "config":
                if args:
                    config_yaml = " ".join(args)
                    try:
                        config_path = config_yaml
                        config_data = yaml.safe_load(config_yaml)
                        if config_data:
                            self.config_path = config_path
                            if config_path and not os.path.isfile(config_path):
                                print(f"Error: The specified configuration file '{config_path}' does not exist.")
                                self.logger.error(f"Error: The specified configuration file '{config_path}' does not "
                                                  f"exist.")
                                client_socket.send(f"Error: The specified configuration file '{config_path}' does not "
                                                   f"exist.".encode())
                            else:
                                client_socket.send("Configuration was added, need to reload with command: reload for "
                                                   "apply changes\n".encode())
                        else:
                            print("Failed to deserialize configuration data.")
                    except Exception as e:
                        print(f"Error deserializing configuration: {str(e)}")
                else:
                    command_handler.send_command_help(client_socket, "config")
            elif action == "reload":
                config_data = self.config_path
                command_handler.reload_task(config_data, client_socket)
            elif action == "help":
                if args:
                    cmd_to_help = args[0]
                    command_handler.send_command_help(client_socket, cmd_to_help)
                else:
                    command_handler.send_help_info(client_socket)
            elif action == "version":
                response = "1.0\n"
                client_socket.send(response.encode())
            elif action == "attach":
                if args:
                    task_name = " ".join(args)
                    if ":" in task_name:
                        group_name, process_name = task_name.split(":")
                        if group_name is not None and len(process_name) > 0:
                            command_handler.attach(client_socket, group_name, process_name)
                        else:
                            response = "Error: Group name and Process name are missing.\n"
                            client_socket.send(response.encode())
                    else:
                        response = "Error: Command should be in the format 'attach group_name:process_name'\n"
                        client_socket.send(response.encode())
            else:
                response = f"*** Unknown syntax: {command}\n"
                client_socket.send(response.encode())

    def run(self):
        self.start()
        while not self.should_exit:
            try:
                readable, _, _ = select.select([self.server_socket] + self.client_sockets, [], [])
                for sock in readable:
                    if sock == self.server_socket:
                        time.sleep(1)
                        client_socket, _ = self.server_socket.accept()
                        self.client_sockets.append(client_socket)
                    else:
                        self.handle_client(sock)
            except KeyboardInterrupt:
                self.shutdown_server()
            except OSError as e:
                if e.errno == 9:
                    self.client_sockets = [sock for sock in self.client_sockets if sock.fileno() != -1]

    def handle_signal(self, signum, frame):
        if signum in (signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
            print(f"Received signal {signum}. Exiting...")
            self.logger.info(f"Received signal {signum}. Exiting...")
            self.shutdown_server()
        elif signum == signal.SIGHUP:
            print("Received SIGHUP signal. Reloading configuration...")
            self.logger.info("Received SIGHUP signal. Reloading configuration...")
            self.reload_configuration()

    def shutdown_server(self):
        for client_socket in self.client_sockets:
            client_socket.close()
        self.server_socket.close()
        self.should_exit = True

    def reload_configuration(self):
        if self.config_path is not None:
            prs = config_parser.create_parser(self.config_path, self.logger)
            self.config = prs.parse()["programs"]
            self.taskmaster.reload(self.config)
        else:
            prs = config_parser.create_parser(None, self.logger)
            self.config = prs.parse()["programs"]
            self.taskmaster.reload(self.config)


def setup_logger():
    # Define the logging format
    log_format = "%(asctime)s [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Log everything to the console
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Taskmaster Server")
    parser.add_argument("socket_path", help="Path to the socket file")

    args = parser.parse_args()

    socket_path = args.socket_path
    setup_logger_debug = setup_logger()
    setup_logger_debug.info(f"Server listen to socket: {socket_path}")
    taskmaster = Taskmaster(setup_logger_debug)
    prs = config_parser.create_parser(None, setup_logger_debug)
    config = prs.parse()["programs"]
    taskmaster.reload(config)
    server = TaskMasterCtlServer(socket_path, taskmaster, config, setup_logger_debug)
    server.run()
