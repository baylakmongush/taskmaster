import os
import sys
import signal

from umask import validate_umask

# Purpose: Parse config file and validate it

def validate_config(config):
    if 'programs' not in config:
        print("Error: 'programs' section is missing in the configuration.")
        return False

    programs = config['programs']
    if not isinstance(programs, dict):
        print("Error: 'programs' must be a dictionary.")
        return False

    for program_name, program_config in programs.items():
        if not isinstance(program_config, dict):
            print(f"Error: Configuration for program '{program_name}' must be a dictionary.")
            return False

        required_params = ['command']
        autorestart = ['never', 'always', 'on_failure']
        stopsignal = [signal.Signals(i).name for i in signal.Signals]

        for param in required_params:
            if param not in program_config:
                print(f"Error: Required parameter '{param}' is missing in the configuration for program '{program_name}'.")
                return False

        if program_config.get('numprocs') is not None and (not isinstance(program_config['numprocs'], int) or program_config['numprocs'] <= 0 or program_config['numprocs'] > 100):
            print(f"Error: 'numprocs' must be a positive integer less than or equal to 100 in the configuration for program '{program_name}'.")
            return False

        if program_config.get('startsecs') is not None and (not isinstance(program_config['startsecs'], int) or program_config['startsecs'] < 0 or program_config['startsecs'] > 3600):
            print(f"Error: 'startsecs' must be a non-negative integer less than or equal to 3600 in the configuration for program '{program_name}'.")
            return False

        if program_config.get('startretries') is not None and (not isinstance(program_config['startretries'], int) or program_config['startretries'] < 0 or program_config['startretries'] > 3600):
            print(f"Error: 'startretries' must be a non-negative integer less than or equal to 3600 in the configuration for program '{program_name}'.")
            return False

        if program_config.get('stopwaitsecs') is not None and (not isinstance(program_config['stopwaitsecs'], int) or program_config['stopwaitsecs'] < 0 or program_config['stopwaitsecs'] > 3600):
            print(f"Error: 'stopwaitsecs' must be a non-negative integer less than or equal to 3600 in the configuration for program '{program_name}'.")
            return False

        if program_config.get('umask') is not None:
            umask_value = program_config['umask']
            validate_umask(umask_value, program_name)

        if program_config.get('stopsignal') is not None and (not isinstance(program_config['stopsignal'], str) or program_config['stopsignal'] not in stopsignal):
            print(f"Error: 'stopsignal' must be a string from the list {stopsignal} in the configuration for program '{program_name}'.")
            return False

        if program_config.get('environment') is not None and (not isinstance(program_config['environment'], dict)):
            print(f"Error: 'environment' must be a dictionary in the configuration for program '{program_name}'.")
            return False

        if not isinstance(program_config['command'], str):
            print(f"Error: 'command' must be a str in the configuration for program '{program_name}'.")
            return False

        if program_config.get('autostart') is not None and (not isinstance(program_config['autostart'], bool)):
            print(f"Error: 'autostart' must be a boolean value in the configuration for program '{program_name}'.")
            return False

        if program_config.get('autorestart') is not None and (not isinstance(program_config['autorestart'], str) or program_config['autorestart'] not in autorestart):
            print(f"Error: 'autorestart' must be a string from the list {autorestart} in the configuration for program '{program_name}'.")
            return False

        if program_config.get('stdout') is not None and (not os.path.exists(program_config['stdout'])):
            print(f"Error: 'stdout' path '{program_config['stdout']}' does not exist for program '{program_name}'.")
            return False

        if program_config.get('stderr') is not None and (not os.path.exists(program_config['stderr'])):
            print(f"Error: 'stderr' path '{program_config['stderr']}' does not exist for program '{program_name}'.")
            return False

        if program_config.get('workingdir') is not None and (not isinstance(program_config['workingdir'], str)):
            print(f"Error: 'workingdir' must be a string in the configuration for program '{program_name}'.")
            return False

    return True
