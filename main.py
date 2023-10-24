import time
import logging

import parser

from taskmaster import Taskmaster

def setup_logger():
    # Define the logging format
    log_format = "%(asctime)s [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Log everything to the console
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

def main():
    prs = parser.create_parser()

    logger = setup_logger()

    taskmaster = Taskmaster(logger)

    config = prs.parse()["programs"]

    taskmaster.reload(config)

    while True:
        time.sleep(1)

        config = prs.parse()["programs"]

        taskmaster.reload(config)


if __name__ == "__main__":
    main()
    
