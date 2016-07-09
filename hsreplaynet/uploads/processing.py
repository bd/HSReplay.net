"""
A module for scheduling UploadEvents to be processed or reprocessed.

For additional details see:
http://boto3.readthedocs.io/en/latest/reference/services/sns.html#SNS.Client.publish
"""
import json
import logging
import os
import boto3
from django.conf import settings
from django.utils.timezone import now
from hsreplaynet.uploads.models import UploadEvent
from hsreplaynet.utils.instrumentation import error_handler, influx_metric


logger = logging.getLogger(__file__)
_sns_client = None


def sns_client():
	global _sns_client
	if not _sns_client:
		_sns_client = boto3.client("sns")
	return _sns_client


def queue_upload_event_for_processing(upload_event_id):
	"""
	This method is used when UploadEvents are initially created.
	However it can also be used to requeue an UploadEvent to be
	processed again if an error was detected downstream that has now been fixed.
	"""
	if settings.IS_RUNNING_LIVE or settings.IS_RUNNING_AS_LAMBDA:
		if "TRACING_REQUEST_ID" in os.environ:
			token = os.environ["TRACING_REQUEST_ID"]
		else:
			# If this was re-queued manually the tracing ID may not be set yet.
			event = UploadEvent.objects.get(id=upload_event_id)
			token = str(event.token.key)

		message = {
			"id": upload_event_id,
			"token": token,
		}

		success = True
		try:
			logger.info("Submitting %r to SNS", message)
			response = sns_client().publish(
				TopicArn=settings.SNS_PROCESS_UPLOAD_EVENT_TOPIC,
				Message=json.dumps({"default": json.dumps(message)}),
				MessageStructure="json"
			)
			logger.info("SNS Response: %s" % str(response))
		except Exception as e:
			logger.error("Exception raised.")
			error_handler(e)
			success = False
		finally:
			influx_metric(
				"queue_upload_event_for_processing",
				fields={"value": 1},
				timestamp=now(),
				tags={
					"success": success,
					"is_running_as_lambda": settings.IS_RUNNING_AS_LAMBDA,
				}
			)
	else:
		logger.info("Processing UploadEvent %r locally", upload_event_id)
		upload = UploadEvent.objects.get(id=upload_event_id)
		upload.process()
