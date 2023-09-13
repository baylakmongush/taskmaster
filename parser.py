import argparse
import yaml
import os


# This class is used to parse the taskmaster.yaml file and return the data as a dictionary
class Parser:

    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        if os.path.isfile(self.file_path) and (self.file_path.lower().endswith('.yaml') or self.file_path.lower().endswith('.yml')):
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
            print("Invalid or missing .conf file: " + self.file_path)


def main():
    # Create an argument parser
    parser = argparse.ArgumentParser(description='Taskmaster Configuration Parser')

    # Add an optional argument for specifying the configuration file
    parser.add_argument('-c', '--config', metavar='CONFIG_FILE', help='Specify the .yaml or .yml configuration file')

    # Parse the command-line arguments
    args = parser.parse_args()

    if args.config:
        # If the -c flag is used, use the specified configuration file
        parser = Parser(args.config)
        print(parser.parse())
    else:
        # Otherwise, use the default 'taskmaster.yaml' file
        parser = Parser('taskmaster.yaml')
        print(parser.parse())


if __name__ == '__main__':
    main()