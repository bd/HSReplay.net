""" A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7 and must be compatible. They should provide
mediation between the AWS Lambda interface and standard Django requests.

"""
import logging, django
from base64 import b64decode
logging.getLogger('boto').setLevel(logging.WARN)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

import pymysql
pymysql.install_as_MySQLdb()
import os, django
import json

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
	result = None
	try:
		result = _raw_log_upload_handler(event, context)
		logger.info("Handler returned the string: %s" % result)
	except ValidationError as e:
		#TODO: Provide additional detailed messaging for ValidationErrors
		logger.exception(e)
		result = {
			"result" : "ERROR",
			"replay_available" : False,
			"msg" : str(e),
			"replay_uuid" : ""
		}

	except Exception as e:
		logger.exception(e)
		result = {
			"result" : "ERROR",
			"replay_available" : False,
			"msg" : str(e),
			"replay_uuid" : ""
		}

	return result

