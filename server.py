import socket


def daemon():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 8888))
    server_socket.listen(5)

    print("Daemon is running and waiting for connections...")

    while True:
        client_socket, address = server_socket.accept()
        print(f"Accepted connection from {address}")

        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            command = data.decode()

        client_socket.close()


if __name__ == "__main__":
    daemon()
