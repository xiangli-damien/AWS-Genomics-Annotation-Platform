# GAS Utilities
This directory contains the following utility-related files:
* `helpers.py` - Miscellaneous helper functions
* `util_config.ini` - Common configuration options for all utility scripts
* `ann_load.py` - Annotator load testing script (if you completed A20)

Each utility must be in its own sub-directory, along with its respective configuration file and run script, as follows:

/notify (for A12)
* `notify.py` - Sends notification email on completion of annotation job
* `notify_config.ini` - Configuration options for notification utility
* `run_notify.sh` - Runs the notifications utility script

/archive (for A14)
If using a script for the archival utility, you must include the following:
* `archive_scipt.py` - Archives free user result files to Glacier using a script
* `archive_script_config.ini` - Configuration options for archive utility script
* `run_archive_scipt.sh` - Runs the archive script

If you implemented the archival utility using a Flask app with a webhook, you must include the following:
* `archive_app.py` - Archives free user result files to Glacier using a Flask app
* `archive_app_config.py` - Configuration options for archive utility Flask app
* `run_archive_app.sh` - Runs the archive Flask app

The archive Flask app must listen on port 5001 (not 5000), as specified in `run_archive_app.sh`.

/thaw  (for A16)
* `thaw_script.py` - Thaws an archived Glacier object using a script
* `thaw_script_config.ini` - Configuration options for thaw utility script
* `run_thaw_scipt.sh` - Runs the thaw script

If you implemented the thawing utility using a Flask app with a webhook, you must include the following:
* `thaw_app.py` - Thaws an archived Glacier object using a Flask app
* `thaw_app_config.py` - Configuration options for thaw utility Flask app
* `run_thaw_app.sh` - Runs the thaw Flask app

The archive Flask app must listen on port 5002 (not 5000), as specified in `run_thaw_app.sh`.

/restore  (for A16)
* `restore.py` - The code for your AWS Lambda function that restores thawed objects to S3

In addition to the above, you must include any other code you used to implement the utility services in their respective directories.
