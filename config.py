"""
module config
Extract arguments from command line or environment.
NOTE: Don't save the TOKEN in the code!

@Author: Denis Maydykovsky
"""

import argparse
import os

# Parse command line
_parser = argparse.ArgumentParser(
    prog="teamlimitsbot",
    usage="python teamlimitsbot [-t TOKEN] [-d DATABASE]"
)

# Treat to the first command line argument as TOKEN.
_parser.add_argument(
    "-t", "--token",
    nargs='?',
    type=str, 
    # Treat to an environment variable 
    default=os.getenv("TEAMLIMITSBOT_TOKEN", None)
    )

_parser.add_argument(
    "-d", "--database",
    nargs='?',
    type=str,
    # Treat to an environment variable
    default=os.getenv("TEAMLIMITSBOT_DATABASE", None)
    )

_args = vars(_parser.parse_args())

# Assign TOKEN variable
_a = _args["token"]
if _a:
    TOKEN = _a

# Assign Database path
_a = _args["database"]
if _a:
    DATABASE = _a


# Self testing
if __name__ == "__main__":
    if "TOKEN" in globals():
        print("Getting TOKEN=", TOKEN)
    else:
        print("TOKEN wasn't taken!")

    if "DATABASE" in globals():
        print("Getting DATABASE", DATABASE)
    else:
        print("DATABASE wasn't taken!")
    


    