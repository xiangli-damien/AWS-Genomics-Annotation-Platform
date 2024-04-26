This directory must contain the annotator related files:
* `annotator.py` - Annotator control script; spawns AnnTools runner
* `run.py` - Runs AnnTools and updates environment on completion
* `annotator_config.ini` - Common configuration options for annotator.py and run.py
* `run_ann.sh` - Runs the annotator script

For those that convert the annotator to run as a Flask app with a webhook, you must include:
* `annotator_webhook.py` - Annotator Flask app
* `annotator_webhook_config.py` - Configuration options for annotator_webhook.
* `run_ann_webhook.py` - Runs the annotator Flask app

The annotator Flask app must listen for requests on port 5000, as defined in `run_ann_webhook.sh`.
