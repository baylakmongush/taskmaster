import threading
import socket
import time

from taskmaster import Process
import parser_config


class CommandHandler:
    def __init__(self, taskmaster, logger):

        self.taskmaster = taskmaster
        self.available_commands = [
            "exit", "reload", "restart",
            "start", "pid", "status",
            "quit", "stop", "version",
            "help"
        ]
        self.command_help = {
            "start": "start <name>\tStart a single process\nstart <gname>:*\t\tStart all processes in a group\nstart <name> <name>\tStart multiple processes or groups\nstart all\t\tStart all processes",
            "stop": "stop <name>\tStop a single process\nstop <gname>:*\t\tStop all processes in a group\nstop <name> <name>\tStop multiple processes or groups\nstop all\t\tStop all processes",
            "status": "status <name>\tGet status for a single process\nstatus <gname>:*\tGet status for all processes in a group\nstatus <name> <name>\tGet status for multiple named processes\nstatus\t\t\tGet all process status info",
            "restart": "restart\t\tRestart the remote taskmasterd",
            "reload": "reload\t\tReload configuration file",
            "help": "help\t\tPrint a list of available actions\nhelp <action>\t\tPrint help for <action>",
            "quit": "quit\t\tExit the taskmasterd shell.",
            "exit": "exit\t\tExit the taskmasterd shell.",
            "version": "version\t\tShow the version of the remote taskmasterd process",
            "pid": "pid <name>\tGet pid for a single process\npid <gname>:*\t\tGet pid for all processes in a group\npid <name> <name>\tGet pid for multiple named processes\npid\t\t\tGet all process pid info",
            "config": "config <path>\t\tReload configuration file from path and use command reload to apply changes"
        }
        self.program_status = {}
        self.logger = logger

    def get_total_processes_in_group(self, group_name, process_name):
        status = self.taskmaster.status(group_name, process_name if len(process_name) > 0 else None)
        if isinstance(status, list):
            return len(status)
        elif isinstance(status, Process):
            return 1
        else:
            return 0

    def start_task(self, client_socket, group_name, process_name):
        client_socket.send(str(self.taskmaster.start(group_name, process_name if len(process_name) > 0 else None)).encode())

    def stop_task(self, client_socket, group_name, process_name):
        client_socket.send(str(self.taskmaster.stop(group_name, process_name if len(process_name) > 0 else None)).encode())

    def restart_task(self, client_socket, group_name, process_name):
        client_socket.send(str(self.taskmaster.restart(group_name, process_name if len(process_name) > 0 else None)).encode())

    def get_pid(self, client_socket, group_name, process_name):
        result: int = self.taskmaster.pid(group_name, process_name)
        if result > 0:
            response = str(result) + "\n"
        else:
            response = f"{group_name}:{process_name} UNKNOWN\n"
        client_socket.send(response.encode())

    def attach(self, client_socket: socket.socket, group_name, process_name):
        while True:
            logs = self.taskmaster.attach(group_name, process_name)

            if logs is None:
                break;

            try:
                client_socket.send(logs.encode())
            except Exception:
                break;

            time.sleep(0.5)

    def get_status(self, client_socket, group_name, process_name):
        response = self.taskmaster.status(group_name, process_name if len(process_name) > 0 else None)

        if isinstance(response, list):
            status_string = ""

            for i in response:
                status_string += str(i) + "\n"
        else:
            status_string = str(response) + "\n"

        client_socket.send(status_string.encode())

    def reload_task(self, config_data, client_socket):
        if config_data is None:
            response = "Error: Invalid configuration or need to add configuration with command: config <path>\n"
            self.logger.error("Error: Invalid configuration or need to add configuration")
        else:
            prs = parser_config.create_parser(config_data, self.logger)
            config_data = prs.parse()["programs"]
            print(config_data)
            self.taskmaster.reload(config_data)
            response = "Configuration updated\n"
            self.logger.info("Configuration updated")
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
