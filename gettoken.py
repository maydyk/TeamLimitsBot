'''
module gettoken
Extract telegram TOKEN from command line or environement.
NOTE: Don't save the TOKEN in the code!

@Author: Denis Maydykovsky
'''

import argparse
import os

# Parse command line
__parser = argparse.ArgumentParser(
    prog="teamlimitsbot",
    usage="python teamlimitsbot [-t TOKEN]"
)

# Treat to the first command line argumant as TOKEN.
__parser.add_argument(
    "-t", "--token",
    nargs='?',
    type=str, 
    # Treat to an enviromenent variable 
    default=os.getenv("TEAMLIMITSBOT_TOKEN", None)
    )
__args = vars(__parser.parse_args())
__t = __args["token"]

# Assign TOKEN variable
if __t:
    TOKEN = __t

# Self testing
if __name__ == "__main__":
    print("Getting TOKEN=", __t)


    