# run.py
#
# Runs the AnnTools pipeline
#
# NOTE: This file lives on the AnnTools instance and
# replaces the default AnnTools run.py
#
# Copyright (C) 2015-2024 Vas Vasiliadis
# University of Chicago
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import shutil
import sys
import time
import driver
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
import argparse
import os

# Get configuration
from configparser import ConfigParser, ExtendedInterpolation

config = ConfigParser(os.environ, interpolation=ExtendedInterpolation())
config.read("annotator_config.ini")

"""A rudimentary timer for coarse-grained profiling
"""


class Timer(object):
    """
    A rudimentary timer for coarse-grained profiling
    """
    def __init__(self, verbose=True):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        if self.verbose:
            print(f"Approximate runtime: {self.secs:.2f} seconds")

def update_dynamodb(job_id, results_bucket, s3_key_result_file, s3_key_log_file):
    """
    Update the DynamoDB entry for the job to include result and log file keys and set status to COMPLETED.
    """
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
    dynamodb = boto3.resource('dynamodb', region_name=config['aws']['AwsRegionName'])
    table = dynamodb.Table(config['gas']['AnnotationsTable'])
    
    # Update the DynamoDB entry with the S3 keys and completion time
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.update_item
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.update_item
    # time.time reference: https://docs.python.org/3/library/time.html

    # Could also add attempts to retry the update in case of failure

    try:
        response = table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET s3_results_bucket=:rb, s3_key_result_file=:rk, s3_key_log_file=:lk, complete_time=:ct, job_status=:js", 
            ExpressionAttributeValues={
                ':rb': results_bucket,
                ':rk': s3_key_result_file,
                ':lk': s3_key_log_file,
                ':ct': int(time.time()), # Convert the current time to an integer
                ':js': 'COMPLETED',
            }
        )
        print(f"Successfully updated DynamoDB for {job_id}, {response}")
        return True
    except ClientError as e:
        # Handle the case where the update fails
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if error_code == 'ConditionalCheckFailedException':
            print(f"Failed to update DynamoDB for {job_id}: Conditional check failed.")
        elif error_code == 'ProvisionedThroughputExceededException':
            print(f"Failed to update DynamoDB for {job_id}: Provisioned throughput exceeded.")
        else:
            print(f"Failed to update DynamoDB for {job_id}: {error_message}")
        return False
    except Exception as e:
        print(f"Failed to update DynamoDB for {job_id}: {str(e)}")
        return False

def upload_file_to_s3(file_path, bucket, s3_key):
    """
    Upload a file to an S3 bucket
    """

    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Upload failed, file not found: {file_path}")
        return False

    # Create an S3 client
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client
    # upload_file reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_file
    s3_client = boto3.client('s3', region_name=config['aws']['AwsRegionName'])
    try:
        print(f"Uploading {file_path} to s3://{bucket}/{s3_key}...")
        # Upload the file to S3
        s3_client.upload_file(file_path, bucket, s3_key)
        print(f"Successfully uploaded {file_path} to s3://{bucket}/{s3_key}")
        return True
    except ClientError as e:
        print(f"Failed to upload {file_path} to {bucket}/{s3_key}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during upload: {e}")
        return False


def delete_local_file(file_path):
    """
    Delete a local file
    """
    try:
        print(f"Deleting {file_path}...")
        os.remove(file_path)
        print(f"Deleted {file_path}")
    except OSError as e:
        print(f"Error deleting {file_path}: {e}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process VCF files and upload results to S3.")
    parser.add_argument('--local_input_file', type=str, required=True, help='Local path to the input VCF file.')
    parser.add_argument('--s3_key', type=str, required=True, help='S3 key where the results will be stored.')
    parser.add_argument('--job_id', type=str, required=True, help='Job ID of the input VCF file.')
    return parser.parse_args()


def main():
    """
    Main function to run the annotation process and upload the results to S3
    """
    # Parse command line arguments
    args = parse_arguments()
    # Extract the input file and S3 key and job_id from the arguments
    job_id = args.job_id
    input_file = args.local_input_file
    s3_key = args.s3_key

    print(f"Processing file {input_file} and uploading to {s3_key}")

    # Get the S3 result bucket name from the configuration
    results_bucket = config['s3']['ResultsBucketName']


    # dirname returns the directory name of the input file (jobs/job_id)
    # dirname reference: https://docs.python.org/3/library/os.path.html
    job_dir = os.path.dirname(input_file)

    # Split the input file name to get the base file name (job_id~test.vcf -> job_id~test)
    base_file_name = os.path.basename(input_file).split('.vcf')[0]
    job_id = base_file_name.split('~')[0]
    # test.vcf -> test.annot.vcf
    output_file = f"{base_file_name}.annot.vcf"
    # test.vcf -> test.vcf.count.log
    log_file = f"{base_file_name}.vcf.count.log"

    # Define the paths for the output and log files (jobs/job_id/test.annot.vcf, jobs/job_id/test.vcf.count.log)
    # join reference: https://docs.python.org/3/library/os.path.html
    # os.path.join reference: https://docs.python.org/3/library/os.path.html
    output_file_path = os.path.join(job_dir, output_file)
    log_file_path = os.path.join(job_dir, log_file)

    s3_key_prefix = os.path.dirname(s3_key)

    # Define the S3 keys for the output and log files
    s3_key_result_file = f"{s3_key_prefix}/{output_file}"
    s3_key_log_file = f"{s3_key_prefix}/{log_file}"

    # Run the AnnTools pipeline

    with Timer():
        driver.run(input_file, 'vcf')  # Assuming driver.run generates the files correctly

    # Upload the output and log files to S3 and delete the local files
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_file
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.download_file
    # Reference: https://docs.python.org/3/library/os.html
    print("Annotation process completed. Starting file uploads...")
    # Upload the output and log files to S3
    output_upload_successful = upload_file_to_s3(output_file_path, results_bucket, s3_key_result_file)
    log_upload_successful = upload_file_to_s3(log_file_path, results_bucket, s3_key_log_file)

    # Check if the files were uploaded successfully
    if output_upload_successful and log_upload_successful:
        print("Both files were successfully uploaded.")
        delete_local_file(output_file_path)
        delete_local_file(log_file_path)
        # Update the DynamoDB entry with the S3 keys and completion time
        if update_dynamodb(job_id, results_bucket, s3_key_result_file, s3_key_log_file):
            print("DynamoDB updated successfully.")
            delete_local_file(input_file)
            try:
                shutil.rmtree(job_dir)  # Remove the job directory if empty
                print("Job directory deleted successfully.")
            except OSError as e:
                print(f"Error deleting job directory {job_dir}: {e}")
        else:
            print("Failed to update DynamoDB.")
    else:
        if not output_upload_successful:
            print(f"Failed to upload output file: {output_file_path}")
        if not log_upload_successful:
            print(f"Failed to upload log file: {log_file_path}")
        print("Files retained due to upload failure.")



if __name__ == "__main__":
    main()

### EOF
