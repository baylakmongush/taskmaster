import sys
import time
import random

if __name__ == "__main__":
    try:
        delay = int(sys.argv[1])
    except Exception:
        delay = 1

    while True:
        time.sleep(delay)

        if bool(random.getrandbits(1)):
            sys.exit(-1)
