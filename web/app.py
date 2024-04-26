#
# Copyright (C) 2015-2023 Vas Vasiliadis
# University of Chicago
#
# Configure GAS runtime environment
# Setup loggers, create DB connection, import all GAS packages
#
# ************************************************************************
#
# DO NOT MODIFY THIS FILE IN ANY WAY.
#
# ************************************************************************
##
__author__ = "Vas Vasiliadis <vas@uchicago.edu>"

import json
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.url_map.strict_slashes = False

# Add configuration to app object
environment = (
    os.environ["GAS_CONFIG"]
    if ("GAS_CONFIG" in os.environ)
    else "config.ProductionConfig"
)
app.config.from_object(environment)

# Protect cookies
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# Turn auto escaping on in Jinja templates
from werkzeug.datastructures import ImmutableDict

jinja_options = ImmutableDict(extensions=["jinja2.ext.autoescape", "jinja2.ext.with_"])
app.jinja_env.autoescape = True

# Add CSRF protection
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
csrf.init_app(app)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

# Create a rotating log file handler
if not os.path.exists(app.config["GAS_LOG_FILE_PATH"]):
    os.makedirs(app.config["GAS_LOG_FILE_PATH"])

log_file = app.config["GAS_LOG_FILE_PATH"] + "/" + app.config["GAS_LOG_FILE_NAME"]
log_file_handler = RotatingFileHandler(log_file, maxBytes=500000, backupCount=9)

# Set up a stream handler to write log messages to the console
log_stream_handler = logging.StreamHandler()

# Set the appropriate log level and format for log lines
if app.config["GAS_LOG_LEVEL"] == "INFO":
    log_format = "%(asctime)s %(levelname)s: %(message)s "
    log_file_handler.setLevel(logging.INFO)
    log_stream_handler.setLevel(logging.INFO)
elif app.config["GAS_LOG_LEVEL"] == "DEBUG":
    log_format = (
        "%(asctime)s %(levelname)s: %(message)s " "[in %(pathname)s:%(lineno)d]"
    )
    log_file_handler.setLevel(logging.DEBUG)
    log_stream_handler.setLevel(logging.DEBUG)

log_file_handler.setFormatter(logging.Formatter(log_format))
log_stream_handler.setFormatter(logging.Formatter(log_format))

# Create the WSGI server (werkzeug, gunicorn, etc.) logger
logger = logging.getLogger(app.config["WSGI_SERVER"])

# Add the log handlers to the server logger
logger.addHandler(log_file_handler)
logger.addHandler(log_stream_handler)

# Tell the Flask app's logger to use our log handlers also
app.logger.addHandler(log_file_handler)
app.logger.addHandler(log_stream_handler)

# Tell the Flask app logger to write to the WSGI server logger
app.logger.handlers = logger.handlers

# Set the app log level to the same as the WSGI server's log level
app.logger.setLevel(logger.level)

# Add database handle to the Flask app
db = SQLAlchemy(app)
migrate = Migrate(app, db)

import views
import auth

### EOF
