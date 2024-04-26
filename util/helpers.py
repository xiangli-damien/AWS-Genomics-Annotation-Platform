# helpers.py
#
# Copyright (C) 2015-2024 Vas Vasiliadis
# University of Chicago
#
# Miscellaneous helper functions
#
# ************************************************************************
#
# DO NOT MODIFY THIS FILE IN ANY WAY.
#
# ************************************************************************
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import boto3
import json
import os

from botocore.exceptions import ClientError

# Get util configuration
from configparser import ConfigParser, ExtendedInterpolation

config = ConfigParser(os.environ, interpolation=ExtendedInterpolation())
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), "util_config.ini"))

"""Send email via Amazon SES
"""


def send_email_ses(recipients=None, sender=None, subject=None, body=None):

    ses = boto3.client("ses", region_name=config["aws"]["AwsRegionName"])

    try:
        response = ses.send_email(
            Destination={
                "ToAddresses": (
                    recipients if isinstance(recipients, list) else [recipients]
                )
            },
            Message={
                "Body": {"Text": {"Charset": "UTF-8", "Data": body}},
                "Subject": {"Charset": "UTF-8", "Data": subject},
            },
            Source=(sender if sender else config["gas"]["MailDefaultSender"]),
        )
    except ClientError as e:
        raise e

    return response


import psycopg2
import psycopg2.extras

"""Access user profile in accounts database
"""


def get_user_profile(id=None, db_name=None):
    # Get database connection details from AWS Secrets Manager
    asm = boto3.client("secretsmanager", region_name=config["aws"]["AwsRegionName"])
    try:
        asm_response = asm.get_secret_value(SecretId="rds/accounts_database")
        rds_secret = json.loads(asm_response["SecretString"])
    except ClientError as e:
        raise e

    db_uri = (
        "postgresql://"
        + rds_secret["username"]
        + ":"
        + rds_secret["password"]
        + "@"
        + rds_secret["host"]
        + ":"
        + str(rds_secret["port"])
        + "/"
        + (db_name if db_name else config["gas"]["AccountsDatabase"])
    )

    try:
        # Connect to accounts database and get a cursor
        connection = psycopg2.connect(db_uri)
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Query the database and get the user's profile record
        query_string = f"SELECT * FROM profiles WHERE identity_id = '{id}'"
        cursor.execute(query_string)
        profile = cursor.fetchall()[0]

    except psycopg2.Error as e:
        connection.rollback()

    finally:
        connection.close()

    # Return user profile record as a dict
    return profile


### EOF
