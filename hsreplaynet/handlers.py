""" A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7 and must be compatible. They should provide
mediation between the AWS Lambda interface and standard Django requests.

"""
import logging
from base64 import b64decode
logging.getLogger('boto').setLevel(logging.WARN)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

import pymysql
pymysql.install_as_MySQLdb()
import os, django

#This block properly bootstraps Django for running inside the AWS Lambda Runtime.
os.environ.setdefault('IS_RUNNING_AS_LAMBDA', 'True')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# We import models or anything that indirectly imports models after django.setup() has been invoked.
from lambdas.authorizer import lambda_handler as _token_authorizer
from lambdas.uploads import _raw_log_upload_handler
from django.core.exceptions import ValidationError

def token_authorizer(event, context):
	"""Entry point for the authorization lambda that determines the validity of an upload token."""
	return _token_authorizer(event, context)

def raw_log_upload_handler(event, context):
	"""Entry point for uploading raw log files."""
	# If an exception is thrown we must translate it into a string that the API Gateway can translate into the
	# appropriate HTTP Response code and message.
	try:
		result = _raw_log_upload_handler(event, context)
		logger.info("Handler returned the string: %s" % result)
		return result
	except ValidationError as e:
		logger.exception(e)
		return "VALIDATION_ERROR: %s" % str(e)
	except Exception as e:
		logger.exception(e)
		return "UNKNOWN_ERROR: %s" % str(e)

	return "ERROR_= - UNREACHABLE BLOCK"
