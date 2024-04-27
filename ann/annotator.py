# annotator.py
#
# NOTE: This file lives on the AnnTools instance
#
# Copyright (C) 2013-2023 Vas Vasiliadis
# University of Chicago
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import subprocess
import boto3
import json
import os
import sys
import time
from subprocess import Popen, PIPE
from botocore.exceptions import NoCredentialsError, ClientError, PartialCredentialsError, EndpointConnectionError, ConnectTimeoutError

# Get configuration
from configparser import ConfigParser, ExtendedInterpolation

config = ConfigParser(os.environ, interpolation=ExtendedInterpolation())
config.read("annotator_config.ini")


"""Reads request messages from SQS and runs AnnTools as a subprocess.

Move existing annotator code here
"""


# Connect to DynamoDB and get the table
dynamodb = boto3.resource('dynamodb', region_name=config['aws']['AwsRegionName'])
# Initialize DynamoDB table
table = dynamodb.Table(config['gas']['AnnotationsTable'])
# initialize the s3 client
s3_client = boto3.client('s3', region_name=config['aws']['AwsRegionName'])

# Connect to SQS and get the message queue
sqs = boto3.resource('sqs', region_name=config['aws']['AwsRegionName'])
# Initialize SQS queue
queue = sqs.get_queue_by_name(QueueName=config['sqs']['QueueName'])

# Set the wait time for long polling
wait_time_seconds = int(config['sqs']['WaitTime'])
# Set the maximum number of messages to retrieve
max_number_of_messages = int(config['sqs']['MaxMessages'])

try:
    if not os.path.exists(config['job']['JobDirectory']):
        os.makedirs(config['job']['JobDirectory'])
except OSError as e:
    # Log the error and send a JSON response with the error message
    # OSError could be due to permission issues, disk full, etc.
    print ({
        "code": 500,
        "status": "error",
        "message": f"Server error occurred while creating directory: {str(e)}"
    }), 500

def handle_requests_queue(sqs=None):

    # Read messages from the queue
    print("Polling for messages...")

    # Attempt to read the maximum number of messages from the queue
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.receive_message
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Queue.receive_messages
    try:
        messages = queue.receive_messages(
            AttributeNames=['All'], # Return all message attributes
            MessageAttributeNames=['All'], # Return all message attributes
            MaxNumberOfMessages=max_number_of_messages, # Receive up to 10 messages at once
            WaitTimeSeconds=wait_time_seconds  # Use long polling - DO NOT use sleep() to wait between polls
        )
    except EndpointConnectionError:
        print("Failed to connect to the endpoint of the AWS service")
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            print("Access denied, please check your permissions")
        elif e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
            print("The queue does not exist, check your queue name and configuration")
        else:
            print(f"Client Error occurred: {e}")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
    
    
    for message in messages:
        try:
            # Parse the message body as JSON
            body = json.loads(message.body)
            job_details = json.loads(body['Message'])
            # Extract job details from the message
            job_id = job_details['job_id']
            s3_key_input_file = job_details['s3_key_input_file']
            # only keep the filename for the response (do not include the job_id prefix)
            pure_file_name = job_details['input_file_name']
            # Extract the Bucket name from the message
            s3_bucket = job_details['s3_inputs_bucket']

            # Extract the entire input file name from the S3 key(UUId~filename)
            input_file_name = s3_key_input_file.split('/')[-1]
            # Create a directory for the input file (jobs/job_id)
            user_job_dir = os.path.join(config['job']['JobDirectory'], job_id)
            # Create the local file path (jobs/job_id~filename)
            local_file_path = os.path.join(user_job_dir, input_file_name)

            # Create a directory for the job if it doesn't exist
            # makedir reference: https://docs.python.org/3/library/os.html
            try:
                if not os.path.exists(user_job_dir):
                    os.makedirs(user_job_dir)
            except OSError as e:
                # Log the error and send a JSON response with the error message
                # OSError could be due to permission issues, disk full, etc.
                print ({
                    "code": 500,
                    "status": "error",
                    "message": f"Server error occurred while creating directory: {str(e)}"
                }), 500

            # Download the VCF file from S3
            # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.download_file
            # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
            # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
            # NoCredentialsError ref: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
            # PartialCredentialsError ref: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
            # ClientError ref: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
            try:
                s3_client.download_file(s3_bucket, s3_key_input_file, local_file_path)
                print(f"Downloaded {s3_key_input_file} to {local_file_path}")

                # Spawn a subprocess to run the annotation script
                # ref: https://docs.python.org/3/library/subprocess.html
                # ref: https://docs.python.org/3/library/os.path.html
                # -- reference: https://docs.python.org/3/library/argparse.html
                # subprocess.Popen ref: https://docs.python.org/3/library/subprocess.html#subprocess.Popen
                try:
                    subprocess.Popen(['python', 'run.py', '--local_input_file', local_file_path, '--s3_key', s3_key_input_file, '--job_id', job_id])
                    print(f"Started annotation for {job_id}")

                    try:
                        response = table.update_item(
                            Key={'job_id': job_id},
                            UpdateExpression='SET job_status = :new_status',
                            ConditionExpression='job_status = :current_status',
                            ExpressionAttributeValues={
                                ':new_status': 'RUNNING',
                                ':current_status': 'PENDING'
                            },
                            ReturnValues="ALL_NEW"
                        )
                        print(f"Successfully updated job status {job_id} to RUNNING:", response)
                        
                        # Delete the message from the queue
                        # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Message.delete
                        try:
                            message.delete()
                            print(f"Deleted SQS message for {job_id}")
                        except ClientError as e:
                            error_code = e.response['Error']['Code']
                            if error_code == 'ReceiptHandleIsInvalid':
                                print("Invalid receipt handle provided. The message might have already been deleted or the handle has changed.")
                            elif error_code == 'AccessDenied':
                                print("Permission denied for deleting the message. Check your IAM permissions.")
                            else:
                                print(f"An error occurred while trying to delete the message: {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred while deleting the message: {e}")
                    
                    # Handle the case where the job status is not PENDING
                    except ClientError as e:
                        # Handle the case where the job status is not PENDING
                        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                            print(f"Job status is not PENDING; not updated to RUNNING. {e}")
                            print({"error": "Job status update failed", "message": "Status is not PENDING"}), 409
                        # Handle other client errors
                        else:
                            print(f"Error updating DynamoDB: {e}")
                            print({"error": "Failed to update job status in DynamoDB", "message": str(e)}), 500
                
                except ConnectTimeoutError:
                    print({"code": 408, "status": "error", "message": "Request timed out"}), 408
                # Handle the case where the annotation script fails to execute
                except OSError as e:
                    print({"code": 500, "status": "error", "message": "Failed to execute the annotation script"}), 500
                except ValueError as e:
                    print({"code": 500, "status": "error", "message": "Invalid arguments for the annotation script"}), 500
                except subprocess.SubprocessError as e:
                    print({"code": 500, "status": "error", "message": "Subprocess management error"}), 500
                
            # Handle the case where AWS credentials are missing or incorrect
            except NoCredentialsError:
                print({"code": 403, "status": "error", "message": "Invalid AWS credentials"}), 403
            # Handle the case where AWS credentials are incomplete
            except PartialCredentialsError:
                print({"code": 403, "status": "error", "message": "Incomplete AWS credentials"}), 403
            # Handle the case where the S3 endpoint cannot be reached
            except EndpointConnectionError:
                print({"code": 500, "status": "error", "message": "Cannot connect to the S3 endpoint"}), 500
            # Handle other client errors
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'NoSuchKey':
                    print({"code": 404, "status": "error", "message": "File not found in S3 bucket"}), 404
                else:
                    print({"code": 500, "status": "error", "message": f"Client error: {error_code}"}), 500
            except Exception as e:
                print({"code": 500, "status": "error", "message": str(e)}), 500

        # Handle the case where the message body is not valid JSON
        except json.JSONDecodeError as e:
            print({"code": 400, "status": "error", "message": "Invalid JSON format in message body"}), 400
        # Handle the case where the message body does not contain the expected keys
        except NoCredentialsError:
            print({"code": 403, "status": "error", "message": "Invalid AWS credentials"}), 403
        except PartialCredentialsError:
            print({"code": 403, "status": "error", "message": "Incomplete AWS credentials"}), 403
        except EndpointConnectionError:
            print({"code": 500, "status": "error", "message": "Cannot connect to the S3 endpoint"}), 500
        except ClientError as e:
            print(f"AWS Client error: {str(e)}")
        except Exception as e:
            print(f"Unhandled error: {str(e)}")

    pass


def main():

    # Get handles to queue

    # Poll queue for new results and process them
    while True:
        handle_requests_queue()


if __name__ == "__main__":
    main()

### EOF
