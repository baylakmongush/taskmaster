import socket, json


def daemon():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 8888))
    server_socket.listen(5)

    print("Daemon is running and waiting for connections...")

    while True:
        client_socket, address = server_socket.accept()
        print(f"Accepted connection from {address}")

        while True:
            data = client_socket.recv(4098)
            if not data:
                break

            parametrs = json.loads(data)

        client_socket.close()
        print ('Received', parametrs)
        
        array = parametrs.split(";")
        print (array)
        for ()


if __name__ == "__main__":
    daemon()
