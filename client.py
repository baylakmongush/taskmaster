import socket


def control_program():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("localhost", 8888))

    while True:
        command = input("Enter a command: ")
        client_socket.send(command.encode())


if __name__ == "__main__":
    control_program()
