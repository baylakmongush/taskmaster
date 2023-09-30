import sys
import os

# Purpose: Parse config file and validate it

def validate_config(config):
    if 'programs' not in config:
        print("Error: 'programs' section is missing in the configuration.")
        sys.exit(1)

    programs = config['programs']
    if not isinstance(programs, dict):
        print("Error: 'programs' must be a dictionary.")
        sys.exit(1)

    for program_name, program_config in programs.items():
        if not isinstance(program_config, dict):
            print(f"Error: Configuration for program '{program_name}' must be a dictionary.")
            sys.exit(1)

        required_params = ['command', 'numprocs', 'autostart', 'autorestart', 'exitcodes', 'startsecs', 'startretries',
                           'stopsignal', 'stopwaitsecs', 'stdout', 'stderr', 'environment', 'workingdir', 'umask']
        autorestart = ['never', 'always', 'on_failure']
        for param in required_params:
            if param not in program_config:
                print(f"Error: Required parameter '{param}' is missing in the configuration for program '{program_name}'.")
                sys.exit(1)

        if not isinstance(program_config['numprocs'], int) or program_config['numprocs'] <= 0:
            print(f"Error: 'numprocs' must be a positive integer in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['startsecs'], int) or program_config['startsecs'] < 0:
            print(f"Error: 'startsecs' must be a non-negative integer in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['startretries'], int) or program_config['startretries'] < 0:
            print(f"Error: 'startretries' must be a non-negative integer in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['stopwaitsecs'], int) or program_config['stopwaitsecs'] < 0:
            print(f"Error: 'stopwaitsecs' must be a non-negative integer in the configuration for program '{program_name}'.")
            sys.exit(1)

        if 'umask' in program_config:
            umask_value = program_config['umask']
            if isinstance(umask_value, int) and 0 <= umask_value <= 0o777:
                if umask_value != os.umask(umask_value):
                    print(
                        f"Error: 'umask' value ({umask_value:o}) does not match the system's umask ({os.umask():o}) in the configuration for program '{program_name}'.")
                    sys.exit(1)
            elif isinstance(umask_value, str):
                try:
                    umask_value = int(umask_value, 8)
                    if 0 <= umask_value <= 0o777:
                        if umask_value != os.umask(umask_value):
                            print(
                                f"Error: 'umask' value ({umask_value:o}) does not match the system's umask ({os.umask():o}) in the configuration for program '{program_name}'.")
                            sys.exit(1)
                    else:
                        print(
                            f"Error: 'umask' value ({umask_value:o}) is not a valid octal value in the configuration for program '{program_name}'.")
                        sys.exit(1)
                except ValueError:
                    print(
                        f"Error: 'umask' value '{umask_value}' is not a valid integer or octal string in the configuration for program '{program_name}'.")
                    sys.exit(1)

        if not isinstance(program_config['stopsignal'], str):
            print(f"Error: 'stopsignal' must be a string in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['environment'], dict):
            print(f"Error: 'environment' must be a dictionary in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['command'], str):
            print(f"Error: 'command' must be a string in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['autostart'], bool):
            print(f"Error: 'autostart' must be a boolean value in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['autorestart'], str) or program_config['autorestart'] not in autorestart:
            print(f"Error: 'autorestart' must be a string from the list {autorestart} in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['stdout'], str):
            print(f"Error: 'stdout' must be a string in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['stderr'], str):
            print(f"Error: 'stderr' must be a string in the configuration for program '{program_name}'.")
            sys.exit(1)

        if not isinstance(program_config['workingdir'], str):
            print(f"Error: 'workingdir' must be a string in the configuration for program '{program_name}'.")
            sys.exit(1)