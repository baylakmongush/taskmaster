import select
import socket
import os
from serialization import deserialize_config
from command_handler import CommandHandler
import logging
import parser
from taskmaster import Taskmaster
import signal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/server.log'
)

class TaskMasterCtlServer:
    def __init__(self, socket_path, taskmaster):
        self.socket_path = socket_path
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.should_exit = False
        self.taskmaster = taskmaster
        self.client_sockets = []

    def start(self):
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGQUIT, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)
        signal.signal(signal.SIGUSR2, self.handle_signal)
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)

    def handle_client(self, client_socket):
        command_handler = CommandHandler(self.taskmaster)
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
                        response = "Error: Command should be in the format 'status group_name:process_name'\n"
                        client_socket.send(response.encode())
                else:
                    command_handler.get_status(client_socket, None)
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
            elif action == "reload":
                if args:
                    config_str = " ".join(args)
                    config_data = deserialize_config(config_str)
                    command_handler.reload(config_data, client_socket)
                else:
                    command_handler.send_command_help(client_socket, "reload")
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
        while not self.should_exit:
            try:
                readable, _, _ = select.select([self.server_socket] + self.client_sockets, [], [])
                for sock in readable:
                    if sock == self.server_socket:
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
            self.shutdown_server()
        elif signum == signal.SIGHUP:
            print("Received SIGHUP signal. Reloading configuration...")
            self.reload_configuration()
        elif signum == signal.SIGUSR2:
            print("Received SIGUSR2 signal. Closing and reopening logs...")
            self.close_and_reopen_logs()

    def shutdown_server(self):
        for client_socket in self.client_sockets:
            client_socket.close()
        self.server_socket.close()
        self.should_exit = True


    def reload_configuration(self):
        # код для перезагрузки конфигурации
        pass

    def close_and_reopen_logs(self):
        # код для закрытия и повторного открытия логов
        pass

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
    socket_path = "sock/taskmaster_socket"
    logging.info(f"Server listen to socket: {socket_path}")
    setup_logger_debug = setup_logger()
    taskmaster = Taskmaster(setup_logger_debug)
    prs = parser.create_parser()
    config = prs.parse()["programs"]
    taskmaster.reload(config)
    server = TaskMasterCtlServer(socket_path, taskmaster)
    server.run()
