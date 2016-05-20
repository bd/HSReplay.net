"""
A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7
and must be compatible.
They should provide mediation between the AWS Lambda interface and
standard Django requests.
"""
import logging
import os
import sys
import django
import pymysql
from django.core.exceptions import ValidationError


logging.getLogger("boto").setLevel(logging.WARN)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

pymysql.install_as_MySQLdb()

# This block properly bootstraps Django for running inside the AWS Lambda Runtime.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
os.environ.setdefault("IS_RUNNING_AS_LAMBDA", "True")
django.setup()

# Make sure django.setup() has already been invoked to import the following
from lambdas.authorizer import lambda_handler as _token_authorizer
from lambdas.uploads import _raw_log_upload_handler


def token_authorizer(event, context):
	"""
	Entry point for the authorization lambda that determines
	the validity of an upload token.
	"""
	return _token_authorizer(event, context)


def raw_log_upload_handler(event, context):
	"""Entry point for uploading raw log files."""
	# If an exception is thrown we must translate it into a string that the API Gateway
	# can translate into the appropriate HTTP Response code and message.
	result = None
	try:
		result = _raw_log_upload_handler(event, context)
		logger.info("Handler returned the string: %s" % result)
	except ValidationError as e:
		# TODO: Provide additional detailed messaging for ValidationErrors
		logger.exception(e)
		result = {
			"result": "ERROR",
			"replay_available": False,
			"msg": str(e),
			"replay_uuid": ""
		}

	except Exception as e:
		logger.exception(e)
		result = {
			"result": "ERROR",
			"replay_available": False,
			"msg": str(e),
			"replay_uuid": ""
		}

	return result
