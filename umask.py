import sys


def is_valid_umask(umask_value):
    try:
        umask_value = int(umask_value, 8)  # Convert to int with base 8 (octal)
        return 0 <= umask_value <= 0o777
    except ValueError:
        return False


def validate_umask(umask_value, program_name):
    if isinstance(umask_value, str) and umask_value != "777":
        if not is_valid_umask(umask_value):
            print(f"{program_name}: {umask_value} - invalid umask (string)")
            sys.exit(1)
    elif isinstance(umask_value, int):
        if not (0 <= umask_value <= 0o777 or umask_value == 777):
            print(f"{program_name}: {umask_value} - invalid umask (integer)")
            sys.exit(1)
    else:
        print(f"{program_name}: {umask_value} - invalid type")
        sys.exit(1)

