#!/usr/bin/env python3

# Simple Script to replace cron for Docker

import os
import argparse
import sys
from subprocess import CalledProcessError, run
from time import sleep, time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interval", help="Time in seconds between runs", type=int)
    args = parser.parse_args()

    print("Running gem mirror every %ds" % args.interval, file=sys.stderr)
    try:
        while True:
            start_time = time()

            try:
                if os.environ['INIT'] == '1':
                    run(['python', '/tmp/download_npm.py', 'sync_all'], check=True)
                else:
                    run(['python', '/tmp/download_npm.py', 'sync_incr'], check=True)
            except CalledProcessError as cpe:
                return cpe.returncode

            run_time = time() - start_time
            if run_time < args.interval:
                sleep_time = args.interval - run_time
                print("Sleeping for %ds" % sleep_time, file=sys.stderr)
                sleep(sleep_time)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
