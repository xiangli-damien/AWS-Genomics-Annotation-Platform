## GAS Web Server
This directory contains the Flask-based web app for the GAS.

Add code to `views.py` and add/update Jinja2 templates in `/templates`. Your constants (e.g., queue names) must be declared in `config.py` and accessed via the `app.config` object.

Your web server must listen for requests on port 4433, as defined in `run_gas.sh`.
