import yaml
import os
import validation


# This class is used to parse the taskmaster.yaml file and return the data as a dictionary
class Parser_config:

    def __init__(self, file_path, logger):
        self.file_path = file_path
        self.logger = logger


    def parse(self):
        if os.path.isfile(self.file_path) and \
                (self.file_path.lower().endswith('.yaml') or self.file_path.lower().endswith('.yml')):
            with open(self.file_path, 'r') as stream:
                try:
                    config_data = yaml.safe_load(stream)
                    if config_data is not None and isinstance(config_data, dict):
                        if validation.validate_config(config_data):
                            return config_data
                        else:
                            print("File content is not a valid YAML dictionary: " + self.file_path)
                            self.logger.error("File content is not a valid YAML dictionary: " + self.file_path)
                            exit(1)
                    else:
                        print("File content is not a valid YAML dictionary: " + self.file_path)
                        self.logger.error("File content is not a valid YAML dictionary: " + self.file_path)
                        exit(1)
                except yaml.YAMLError as exc:
                    if hasattr(exc, 'problem_mark'):
                        mark = exc.problem_mark
                        error_location = f"Line {mark.line + 1}, Column {mark.column + 1}"
                        print(f"YAML parsing error at {error_location}: {exc.problem}")
                        self.logger.error(f"YAML parsing error at {error_location}: {exc.problem}")
                        exit(1)
                    else:
                        print("Error parsing YAML: " + str(exc))
                        self.logger.error("Error parsing YAML: " + str(exc))
                        exit(1)
        else:
            print("Invalid or missing .yaml or .yml file: " + self.file_path)
            self.logger.error("Invalid or missing .yaml or .yml file: " + self.file_path)
            exit(1)


def create_parser(config_path, logger):
    default_config_paths = ['taskmaster.yaml', '/etc/taskmaster.yaml', '/etc/taskmaster/taskmaster.yaml',
                            '/etc/taskmaster.yml', '/etc/taskmaster/taskmaster.yml']

    if config_path is None:
        for path in default_config_paths:
            if os.path.isfile(path):
                config_path = path
                break
            else:
                print("No configuration file provided and no default configuration file found.")
                logger.error("No configuration file provided and no default configuration file found.")
                exit(1)

    config_parser = Parser_config(config_path, logger)
    return config_parser
