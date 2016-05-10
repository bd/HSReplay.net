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

# We import models and other parts of the project after django.setup() has been invoked.
from web.models import HSReplaySingleGameFileUpload
from lambdas.authorizer import lambda_handler as _token_authorizer


def token_authorizer(event, context):
	"""Entry point for the authorization lambda that determines the validity of an upload token."""
	return _token_authorizer(event, context)


def raw_log_upload_handler(event, context):
	query_params = event['query_parameters']
	logger.info("Query Params: %s" % str(query_params))

	b64encoded_log = event['body']
	logger.info("Base 64 Encoded Log:%s" % b64encoded_log)

	raw_log = b64decode(b64encoded_log)
	logger.info("*** Raw Log Data ***\n%s" % raw_log)
	return str(query_params)


def django_models_test(event, context):
	return str(HSReplaySingleGameFileUpload.objects.count())


if __name__ == '__main__':
	print(django_models_test(None, None))