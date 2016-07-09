"""
A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7
and must be compatible.
They should provide mediation between the AWS Lambda interface and
standard Django requests.
"""
import logging
from logging.handlers import SysLogHandler
import os
import django
# This block properly bootstraps Django for running inside the AWS Lambda Runtime.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hsreplaynet.settings")
os.environ.setdefault("IS_RUNNING_AS_LAMBDA", "True")
django.setup()
from django.conf import settings


class TracingIdAwareFormatter(logging.Formatter):
	def format(self, record):
		# Allow usage of the 'token' fmt variable by setting it on the record
		record.token = os.environ.get("TRACING_REQUEST_ID", "unknown-token")
		return super(TracingIdAwareFormatter, self).format(record)


# Add papertrail logger
_handler = SysLogHandler(address=(settings.PAPERTRAIL_HOSTNAME, settings.PAPERTRAIL_PORT))
formatter = TracingIdAwareFormatter(
	"%(asctime)s %(funcName)s: %(token)s: %(message)s",
	datefmt="%b %d %H:%M:%S"
)
_handler.setFormatter(formatter)

lambdas_logger = logging.getLogger("hsreplaynet")
lambdas_logger.addHandler(_handler)
lambdas_logger.setLevel(logging.DEBUG)

logging.getLogger("boto").setLevel(logging.WARN)

# Make sure django.setup() has already been invoked to import handlers
from hsreplaynet.lambdas.authorizer import api_gateway_authorizer as token_authorizer
from hsreplaynet.lambdas.uploads import create_power_log_upload_event_handler
from hsreplaynet.lambdas.uploads import process_upload_event_handler
