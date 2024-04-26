#!/bin/bash

# run_gas.sh
#
# Copyright (C) 2015-2024 Vas Vasiliadis
# University of Chicago
#
# Runs the annotator as a Flask app (with a webhook)
#
##

export ANN_APP_HOME=/home/ubuntu/gas/ann
export SOURCE_HOST=0.0.0.0
export HOST_PORT=5000

cd $ANN_APP_HOME

/home/ubuntu/.virtualenvs/mpcs/bin/uwsgi \
    --chdir $ANN_APP_HOME \
    --enable-threads \
    --http $SOURCE_HOST:$HOST_PORT \
    --log-master \
    --manage-script-name \
    --mount /annotator_webhook=annotator_webhook:app \
    --socket /tmp/annotator_webhook.sock \
    --processes 1 \
    --vacuum

### EOF