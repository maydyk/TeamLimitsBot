"""
module gettoken
Extract telegram TOKEN from command line or environment.
NOTE: Don't save the TOKEN in the code!

@Author: Denis Maydykovsky
"""

import argparse
import os

# Parse command line
_parser = argparse.ArgumentParser(
    prog="teamlimitsbot",
    usage="python teamlimitsbot [-t TOKEN]"
)

# Treat to the first command line argument as TOKEN.
_parser.add_argument(
    "-t", "--token",
    nargs='?',
    type=str, 
    # Treat to an environment variable 
    default=os.getenv("TEAMLIMITSBOT_TOKEN", None)
    )
_args = vars(_parser.parse_args())
_t = _args["token"]

# Assign TOKEN variable
if _t:
    TOKEN = _t

# Self testing
if __name__ == "__main__":
    print("Getting TOKEN=", _t)


    