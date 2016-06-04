"""
A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7
and must be compatible.
They should provide mediation between the AWS Lambda interface and
standard Django requests.
"""
import logging
import os
import django
import pymysql


logging.getLogger("boto").setLevel(logging.WARN)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

pymysql.install_as_MySQLdb()

# This block properly bootstraps Django for running inside the AWS Lambda Runtime.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hsreplaynet.settings")
os.environ.setdefault("IS_RUNNING_AS_LAMBDA", "True")
django.setup()

# Make sure django.setup() has already been invoked to import handlers
from hsreplaynet.lambdas.authorizer import lambda_handler as token_authorizer
from hsreplaynet.lambdas.uploads import raw_log_upload_handler, create_power_log_upload_event_handler
