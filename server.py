import socket
import json
import sys


def daemon():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 8888))
    server_socket.listen(5)

    print("Daemon is running and waiting for connections...")

    try:
        while True:
            client_socket, address = server_socket.accept()
            print(f"Accepted connection from {address}")

            while True:
                data = client_socket.recv(4098)
                if not data:
                    break

                program_data = json.loads(data.decode('utf-8'))

                # Check if there are programs to process
                if 'programs' in program_data:
                    programs = program_data['programs']

                    # Loop through each program
                    for program_name, program_details in programs.items():
                        print(f"Received program: {program_name}")

                        # Process the "server" array if it exists
                        if 'server' in program_details:
                            server_array = program_details['server']
                            print("Server array:")
                            for server_item in server_array:
                                print(server_item)

                        # Process other program details as needed
                        for key, value in program_details.items():
                            if key == 'environment':
                                print("Environment:")
                                for env_key, env_value in value.items():
                                    print(f"{env_key}: {env_value}")
                            else:
                                print(f"{key}: {value}")

            client_socket.close()
            print('Data received and processed')

    except KeyboardInterrupt:
        print("\nServer interrupted. Cleaning up and exiting...")
        server_socket.close()
        sys.exit(0)


if __name__ == "__main__":
    daemon()
