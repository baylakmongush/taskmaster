import json
import socket
import sys


def get_input(prompt, data_type, error_message):
    while True:
        try:
            user_input = data_type(input(prompt))
            return user_input
        except ValueError:
            print(error_message)


def safe_input(prompt):
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\nInput interrupted. Please try again.")
        return None


def validate_boolean_input(prompt):
    while True:
        user_input = input(prompt).lower()
        if user_input == "true":
            return True
        elif user_input == "false":
            return False
        else:
            print("Please enter 'true' or 'false'.")


def validate_yes_no_input(prompt):
    while True:
        user_input = input(prompt).lower()
        if user_input == "yes":
            return True
        elif user_input == "no":
            return False
        else:
            print("Please enter 'yes' or 'no'.")


def add_program(programs):
    program_name = input("Enter program name: ")
    programs[program_name] = {
        "command": input("Enter command: "),
        "numprocs": get_input("Enter numprocs: ", int, "Please enter a valid integer for numprocs."),
        "autostart": validate_boolean_input("Enter autostart (true/false): "),
        "autorestart": validate_boolean_input("Enter autorestart (true/false): "),
        "exitcodes": [],  # Initialize as an empty list
        "startsecs": get_input("Enter startsecs: ", int, "Please enter a valid integer for startsecs."),
        "startretries": get_input("Enter startretries: ", int, "Please enter a valid integer for startretries."),
        "stopsignal": input("Enter stopsignal: "),
        "stopwaitsecs": get_input("Enter stopwaitsecs: ", int, "Please enter a valid integer for stopwaitsecs."),
        "stdout": input("Enter stdout: "),
        "stderr": input("Enter stderr: "),
        "environment": {},
        "workingdir": input("Enter workingdir: "),
        "umask": input("Enter umask: ")
    }

    exitcodes_count = get_input("Enter exitcodes_count: ", int, "Please enter a valid integer for exitcodes_count.")
    for i in range(exitcodes_count):
        exitcode = get_input(f"Enter exit code {i + 1}: ", int, "Please enter a valid integer for exit code.")
        programs[program_name]["exitcodes"].append(exitcode)

    environment_count = get_input("Enter environment_count: ", int, "Please enter a valid integer for environment_count.")
    for i in range(environment_count):
        key = input(f"Enter ENV_VAR{i + 1}: ")
        value = safe_input(f"Enter value for ENV_VAR{i + 1}: ")
        if value is None:
            continue
        programs[program_name]["environment"][key] = value


def control_program():
    try:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(("localhost", 8888))
        except ConnectionRefusedError:
            print("Error: The server is not running or refused the connection.")
            return

        programs = {}

        while True:
            add_program(programs)
            another_program = validate_yes_no_input("Add another program? (yes/no): ")
            if not another_program:
                break

        data = json.dumps({"programs": programs}).encode('utf-8')
        client_socket.send(data)
        print('Sent data')

    except KeyboardInterrupt:
        print("\nServer interrupted. Cleaning up and exiting...")
        client_socket.close()
        sys.exit(0)
    except EOFError:
        print("Error: End of input reached. Please provide a program name.")
        client_socket.close()
        sys.exit(0)


if __name__ == "__main__":
    control_program()
