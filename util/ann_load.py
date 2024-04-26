# ann_load.py
#
# Copyright (C) 2015-2023 Vas Vasiliadis
# University of Chicago
#
# Exercises the annotator's auto scaling
#
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import boto3
import json
import sys
import time
import uuid

from botocore.exceptions import ClientError

# Define constants here; no config file is used for this scipt
USER_ID = "<UUID_for_your_Globus_Auth_identity>"
EMAIL = "<CNetID>@uchicago.edu"

"""Fires off annotation jobs with hardcoded data for testing
"""


def load_requests_queue():

    # Define job data

    # Persist job data to database

    # Send message to request topic

    pass


def main():
    while True:
        try:
            load_requests_queue()
            time.sleep(3)
        except ClientError as e:
            print("Irrecoverable error. Exiting.")
            sys.exit()


if __name__ == "__main__":
    main()

### EOF
