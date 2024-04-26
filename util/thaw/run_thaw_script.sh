#!/bin/bash

# run_thaw_script.sh
#
# Copyright (C) 2015-2024 Vas Vasiliadis
# University of Chicago
#
# Runs the Glacier thawing utility script
#
##

cd /home/ubuntu/gas/util/thaw
source /home/ubuntu/.virtualenvs/mpcs/bin/activate
/home/ubuntu/.virtualenvs/mpcs/bin/python /home/ubuntu/gas/util/thaw/thaw_script.py

### EOF