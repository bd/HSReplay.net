"""
A module for scheduling UploadEvents to be processed or reprocessed.

For additional details see:
http://boto3.readthedocs.io/en/latest/reference/services/sns.html#SNS.Client.publish
"""
import json
import logging
import boto3
from django.conf import settings
from django.utils.timezone import now
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
		logger.info("UploadEvent %s will be submitted to SNS." % (upload_event_id))

		topic_arn = settings.SNS_PROCESS_UPLOAD_EVENT_TOPIC
		message = {"upload_event_id": upload_event_id}

		logger.info("The TopicARN is %s" % topic_arn)
		success = True
		try:
			response = sns_client().publish(
				TopicArn=topic_arn,
				Message=json.dumps({"default": json.dumps(message)}),
				MessageStructure="json"
			)
			logger.info("SNS Response: %s" % str(response))
		except Exception as e:
			logger.error("Exception raised.")
			error_handler(e)
			success = False
		else:
			message_id = response["MessageId"]
			logger.info("The submitted message ID is: %s" % message_id)
			return message_id

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
		from .models import UploadEvent

		logger.info("Processing UploadEvent %r locally", upload_event_id)
		upload = UploadEvent.objects.get(id=upload_event_id)
		upload.process()
