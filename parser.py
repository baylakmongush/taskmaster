import argparse
import yaml
import os


# This class is used to parse the taskmaster.yaml file and return the data as a dictionary
class Parser:

    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        if os.path.isfile(self.file_path) and \
                (self.file_path.lower().endswith('.yaml') or self.file_path.lower().endswith('.yml')):
            with open(self.file_path, 'r') as stream:
                try:
                    config_data = yaml.safe_load(stream)
                    if config_data is not None and isinstance(config_data, dict):
                        return config_data
                    else:
                        print("File content is not a valid YAML dictionary: " + self.file_path)
                except yaml.YAMLError as exc:
                    if hasattr(exc, 'problem_mark'):
                        # Get the error location in the file
                        mark = exc.problem_mark
                        error_location = f"Line {mark.line + 1}, Column {mark.column + 1}"
                        print(f"YAML parsing error at {error_location}: {exc.problem}")
                    else:
                        print("Error parsing YAML: " + str(exc))
        else:
            print("Invalid or missing .yaml or .yml file: " + self.file_path)


def main():
    default_config_paths = ['/etc/taskmaster.yaml', '/etc/taskmaster/taskmaster.yaml', '/etc/taskmaster.yml', '/etc/taskmaster/taskmaster.yml']

    parser = argparse.ArgumentParser(description='Taskmaster')
    parser.add_argument('-c', '--config', type=str, help='Path to the configuration file')
    args = parser.parse_args()

    if args.config is not None:
        config_path = args.config
    else:
        for path in default_config_paths:
            if os.path.isfile(path):
                config_path = path
                break
        else:
            print("No configuration file provided and no default configuration file found.")
            return

    config_parser = Parser(config_path)
    config_data = config_parser.parse()
    if config_data:
        print("Configuration data loaded successfully.")
    else:
        print("Failed to load configuration data.")


if __name__ == '__main__':
    main()