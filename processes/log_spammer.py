import os
import sys
import time

if __name__ == "__main__":
    counter = 0

    while True:
        print(f"Hello, I'm log message number {counter}")

        sys.stdout.flush()

        counter += 1

        time.sleep(1)
