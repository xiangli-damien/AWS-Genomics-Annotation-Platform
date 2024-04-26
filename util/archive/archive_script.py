# archive_script.py
#
# Archive free user data
#
# Copyright (C) 2015-2023 Vas Vasiliadis
# University of Chicago
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import boto3
import time
import os
import sys
import json
from botocore.exceptions import ClientError

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import ConfigParser, ExtendedInterpolation

config = ConfigParser(os.environ, interpolation=ExtendedInterpolation())
config.read("../util_config.ini")
config.read("archive_script_config.ini")

"""A14
Archive free user results files
"""


def handle_archive_queue(sqs=None):

    # Read messages from the queue

    # Process messages --> archive results file

    # Delete messages

    pass


def main():

    # Get handles to SQS

    # Poll queue for new results and process them
    while True:
        handle_archive_queue()


if __name__ == "__main__":
    main()

### EOF
