# annotator.py
#
# NOTE: This file lives on the AnnTools instance
#
# Copyright (C) 2013-2023 Vas Vasiliadis
# University of Chicago
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import boto3
import json
import os
import sys
import time
from subprocess import Popen, PIPE
from botocore.exceptions import ClientError

# Get configuration
from configparser import ConfigParser, ExtendedInterpolation

config = ConfigParser(os.environ, interpolation=ExtendedInterpolation())
config.read("annotator_config.ini")


"""Reads request messages from SQS and runs AnnTools as a subprocess.

Move existing annotator code here
"""


def handle_requests_queue(sqs=None):

    # Read messages from the queue

    # Process messages

    # Delete messages

    pass


def main():

    # Get handles to queue

    # Poll queue for new results and process them
    while True:
        handle_requests_queue()


if __name__ == "__main__":
    main()

### EOF
