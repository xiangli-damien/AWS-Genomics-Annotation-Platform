# views.py
#
# Copyright (C) 2015-2023 Vas Vasiliadis
# University of Chicago
#
# Application logic for the GAS
#
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import uuid
import time
import json
from datetime import datetime

import boto3
from botocore.config import Config 
from botocore.exceptions import NoCredentialsError, ClientError, EndpointConnectionError
from botocore.client import Config
from boto3.dynamodb.conditions import Key

from flask import abort, flash, redirect, render_template, request, session, url_for, jsonify

from app import app, db
from decorators import authenticated, is_premium

"""Start annotation request
Create the required AWS S3 policy document and render a form for
uploading an annotation input file using the policy document

Note: You are welcome to use this code instead of your own
but you can replace the code below with your own if you prefer.
"""


@app.route("/annotate", methods=["GET"])
@authenticated
def annotate():
    """
    Generates a pre-signed POST request for S3 and renders a form for file uploading.
    Redirects upon successful upload to process the file.
    """
    # Create an S3 client
    s3 = boto3.client(
        "s3",
        region_name=app.config["AWS_REGION_NAME"],
        config=Config(signature_version="s3v4"),
    )
    # Generate a unique file ID and S3 key
    # python uuid: https://docs.org/3/library/uuid.html
    unique_file_id = str(uuid.uuid4())
    # Extract the bucket name from the app configuration
    bucket_name = app.config["AWS_S3_INPUTS_BUCKET"]
    # Define the urser ID
    user_id = session["primary_identity"]
    # Generate unique ID to be used as S3 key (name)
    key_name = (
        app.config["AWS_S3_KEY_PREFIX"]
        + user_id
        + "/"
        + unique_file_id
        + "~${filename}"
    )

    # Create the redirect URL
    redirect_url = str(request.url) + "/job"
    # Define the server-side encryption algorithm
    encryption = app.config["AWS_S3_ENCRYPTION"]
    # Define policy conditions
    acl = app.config["AWS_S3_ACL"]
    # Define the form fields and conditions
    fields = {
        "success_action_redirect": redirect_url,
        "x-amz-server-side-encryption": encryption,
        "acl": acl,
        "csrf_token": app.config["SECRET_KEY"],
    }
    conditions = [
        ["starts-with", "$success_action_redirect", redirect_url],
        {"x-amz-server-side-encryption": encryption},
        {"acl": acl},
        ["starts-with", "$csrf_token", ""],
    ]

    try:
        # python boto3: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
        # Generate the presigned POST call
        presigned_post = s3.generate_presigned_post(
            Bucket=bucket_name,
            Key=key_name,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=app.config["AWS_SIGNED_REQUEST_EXPIRATION"],
        )
    except NoCredentialsError as e:
        # Return an error message if we fail to generate the pre-signed POST request.
        # NoCredentialsError reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
        app.logger.error(f"Unable to generate presigned URL: {e}")
        abort(500)
    except EndpointConnectionError:
        # Handle the case where we cannot connect to the S3 endpoint.
        # EndpointConnectionError reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
        app.logger.error("Cannot connect to the S3 endpoint.")
        abort(500)
    except ClientError as e:
        # Handle all client errors
        # ClientError reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
        # if the error is due to invalid credentials
        if e.response['Error']['Code'] == 'InvalidAccessKeyId':
            app.logger.error("Invalid AWS Access Key ID")
            abort(500)
        # if the error is due to invalid secret key
        elif e.response['Error']['Code'] == 'SignatureDoesNotMatch':
            app.logger.error("The request signature we calculated does not match")
            abort(500)
        else:
            app.logger.error(f"Unexpected error: {e}")
            abort(500)
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        abort(500)

    # Render the upload form which will parse/submit the presigned POST
    return render_template(
        "annotate.html", s3_post=presigned_post, role=session["role"]
    )


"""Fires off an annotation job
Accepts the S3 redirect GET request, parses it to extract 
required info, saves a job item to the database, and then
publishes a notification for the annotator service.

Note: Update/replace the code below with your own from previous
homework assignments
"""


@app.route("/annotate/job", methods=["GET"])
def create_annotation_job_request():
    """
    Handles redirection from S3 after file upload, persists job details in DynamoDB,
    and notifies the annotation service.
    """

    # Get the region name from the app configuration
    region = app.config["AWS_REGION_NAME"]
    dynamodb_table = app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"]

    # Parse redirect URL query parameters for S3 object info
    bucket_name = request.args.get("bucket")
    s3_key = request.args.get("key")

    # Extract the job ID from the S3 key
    job_id = s3_key.split('/')[2].split('~')[0]

    # Extract the user ID from the S3 key
    user_id = session.get('primary_identity', 'unknown')

    # Get the current timestamp
    submit_time = int(time.time())

    # input_file_name with out job_id
    input_file_name = s3_key.split('/')[-1]
    # only keep the filename without uuid for the response
    pure_file_name = input_file_name.split('~')[-1] if '~' in input_file_name else input_file_name

    # Prepare the job details
    data = {
        "job_id": job_id,
        "user_id": user_id,
        "input_file_name": pure_file_name,
        "s3_inputs_bucket": bucket_name,
        "s3_key_input_file": s3_key,
        "submit_time": submit_time,
        "job_status": "PENDING"
    }

    # Create a DynamoDB client
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(dynamodb_table)

    # Insert the job details into DynamoDB
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html
    # table.put_item reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.put_item
    try:
        table.put_item(Item=data)
    except ClientError as e:
        return jsonify({"error": "DynamoDB ClientError", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Unexpected error while updating DynamoDB", "message": str(e)}), 500
    
    # Create an SNS client
    sns_client = boto3.client('sns', region_name=region)
    
    # Create an SNS client
    try:
        response = sns_client.publish(
            TopicArn=app.config["AWS_SNS_JOB_REQUEST_TOPIC_A10"],
            Message=json.dumps({"default": json.dumps(data)}),
            MessageStructure='json'
        )

    except ClientError as e:
        # Handle the case where the SNS publish fails
        if e.response['Error']['Code'] == 'AccessDenied':
            app.logger.error(f"Access denied to SNS: {e}")
            abort(403)
        else:
            app.logger.error(f"Failed to publish job to SNS: {e}")
            abort(500)
    except Exception as e:
        app.logger.error(f"Unexpected error (failed to upload to SNS): {e}")
        abort(500)

    # Send a notification to the annotator service
    return render_template("annotate_confirm.html", job_id=job_id)


"""List all annotations for the user
"""


@app.route("/annotations", methods=["GET"])
def annotations_list():

    return render_template("annotations.html", annotations=None)



"""Display details of a specific annotation job
"""


@app.route("/annotations/<id>", methods=["GET"])
def annotation_details(id):
    pass


"""Display the log file contents for an annotation job
"""


@app.route("/annotations/<id>/log", methods=["GET"])
def annotation_log(id):
    pass


"""Subscription management handler
"""
import stripe
from auth import update_profile


@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if request.method == "GET":
        # Display form to get subscriber credit card info

        # If A15 not completed, force-upgrade user role and initiate restoration
        pass

    elif request.method == "POST":
        # Process the subscription request

        # Create a customer on Stripe

        # Subscribe customer to pricing plan

        # Update user role in accounts database

        # Update role in the session

        # Request restoration of the user's data from Glacier
        # ...add code here to initiate restoration of archived user data
        # ...and make sure you handle files pending archive!

        # Display confirmation page
        pass


"""DO NOT CHANGE CODE BELOW THIS LINE
*******************************************************************************
"""

"""Set premium_user role
"""


@app.route("/make-me-premium", methods=["GET"])
@authenticated
def make_me_premium():
    # Hacky way to set the user's role to a premium user; simplifies testing
    update_profile(identity_id=session["primary_identity"], role="premium_user")
    return redirect(url_for("profile"))


"""Reset subscription
"""


@app.route("/unsubscribe", methods=["GET"])
@authenticated
def unsubscribe():
    # Hacky way to reset the user's role to a free user; simplifies testing
    update_profile(identity_id=session["primary_identity"], role="free_user")
    return redirect(url_for("profile"))


"""Home page
"""


@app.route("/", methods=["GET"])
def home():
    return render_template("home.html"), 200


"""Login page; send user to Globus Auth
"""


@app.route("/login", methods=["GET"])
def login():
    app.logger.info(f"Login attempted from IP {request.remote_addr}")
    # If user requested a specific page, save it session for redirect after auth
    if request.args.get("next"):
        session["next"] = request.args.get("next")
    return redirect(url_for("authcallback"))


"""404 error handler
"""


@app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "error.html",
            title="Page not found",
            alert_level="warning",
            message="The page you tried to reach does not exist. \
      Please check the URL and try again.",
        ),
        404,
    )


"""403 error handler
"""


@app.errorhandler(403)
def forbidden(e):
    return (
        render_template(
            "error.html",
            title="Not authorized",
            alert_level="danger",
            message="You are not authorized to access this page. \
      If you think you deserve to be granted access, please contact the \
      supreme leader of the mutating genome revolutionary party.",
        ),
        403,
    )


"""405 error handler
"""


@app.errorhandler(405)
def not_allowed(e):
    return (
        render_template(
            "error.html",
            title="Not allowed",
            alert_level="warning",
            message="You attempted an operation that's not allowed; \
      get your act together, hacker!",
        ),
        405,
    )


"""500 error handler
"""


@app.errorhandler(500)
def internal_error(error):
    return (
        render_template(
            "error.html",
            title="Server error",
            alert_level="danger",
            message="The server encountered an error and could \
      not process your request.",
        ),
        500,
    )


"""CSRF error handler
"""


from flask_wtf.csrf import CSRFError


@app.errorhandler(CSRFError)
def csrf_error(error):
    return (
        render_template(
            "error.html",
            title="CSRF error",
            alert_level="danger",
            message=f"Cross-Site Request Forgery error detected: {error.description}",
        ),
        400,
    )


### EOF
