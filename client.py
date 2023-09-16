import json, socket


def control_program():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("localhost", 8888))

    parameters = [
        'command', 
        'numprocs', 
        'autostart',
        'autorestart',
        'exitcodes',
        'startsecs',
        'startretries',
        'stopsignal',
        'stopwaitsecs',
        'stdout',
        'stderr',
        'environment_count',
        'environment',
        'ENV_VAR',
        'workingdir',
        'umask']

    array = ""

    while True:
        
        for param in parameters:
            array += "%s:" % param + input("Enter %s: " % param) + ";"
        break

    data = json.dumps(array).encode('utf-8')
    client_socket.send(data)
    print('Sent data')
        
        


if __name__ == "__main__":
    control_program()
