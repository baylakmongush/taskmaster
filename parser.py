import yaml
import os


# This class is used to parse the config.yml file and return the data as a dictionary
class Parser:

    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        if os.path.isfile(self.file_path):
            with open(self.file_path, 'r') as stream:
                try:
                    return yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
        else:
            print("File not found: " + self.file_path)

# if __name__ == '__main__':
#     parser = Parser('config.yml')
#     print(parser.parse())
