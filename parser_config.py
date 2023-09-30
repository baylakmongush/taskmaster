import yaml
import os
from validation import validate_config

def parse_config(config_file):
    with open(config_file, 'r') as file:
        try:
            config = yaml.safe_load(file)
            validate_config(config)
            return config
        except yaml.YAMLError as e:
            print(f"Ошибка при чтении конфигурационного файла: {e}")
            return None


class Parser:
    def __init__(self):
        self.config_data = None

    def parse_from_file(self, file_path):
        if os.path.isfile(file_path) and \
                (file_path.lower().endswith('.yaml') or file_path.lower().endswith('.yml')):
            with open(file_path, 'r') as stream:
                try:
                    config_data = yaml.safe_load(stream)
                    if config_data is not None and isinstance(config_data, dict):
                        self.config_data = config_data
                        validate_config(config_data)
                    else:
                        print("File content is not a valid YAML dictionary: " + file_path)
                except yaml.YAMLError as exc:
                    if hasattr(exc, 'problem_mark'):
                        mark = exc.problem_mark
                        error_location = f"Line {mark.line + 1}, Column {mark.column + 1}"
                        print(f"YAML parsing error at {error_location}: {exc.problem}")
                    else:
                        print("Error parsing YAML: " + str(exc))
        else:
            print("Invalid or missing .yaml or .yml file: " + file_path)

    def parse_from_default_paths(self):
        default_config_paths = [
            '/etc/taskmaster.yaml',
            '/etc/taskmaster/taskmaster.yaml',
            '/etc/taskmaster.yml',
            '/etc/taskmaster/taskmaster.yml',
            './taskmaster.yaml'
        ]

        for path in default_config_paths:
            if os.path.isfile(path):
                self.parse_from_file(path)
                return

    def get_config_data(self):
        return self.config_data
