# thaw_script.py
#
# Thaws upgraded (premium) user data
#
# Copyright (C) 2015-2024 Vas Vasiliadis
# University of Chicago
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import boto3
import json
import os
import sys
import time

from botocore.exceptions import ClientError

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import ConfigParser, ExtendedInterpolation

config = ConfigParser(os.environ, interpolation=ExtendedInterpolation())
config.read("../util_config.ini")
config.read("thaw_script_config.ini")

"""A16
Initiate thawing of archived objects from Glacier
"""


def handle_thaw_queue(sqs=None):

    # Read messages from the queue

    # Process messages --> initiate restore from Glacier

    # Delete messages

    pass


def main():

    # Get handles to resources

    # Poll queue for new results and process them
    while True:
        handle_thaw_queue()


if __name__ == "__main__":
    main()

### EOF
