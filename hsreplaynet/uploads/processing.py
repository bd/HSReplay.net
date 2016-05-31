"""A module for scheduling UploadEvents to be processed or reprocessed.

For additional details see:
http://boto3.readthedocs.io/en/latest/reference/services/sns.html#SNS.Client.publish
"""
import json
import logging
import boto3
from django.conf import settings
from django.utils.timezone import now
from hsreplaynet.instrumentation import error_handler, influx_metric
from hsreplaynet.uploads.models import UploadEventProcessingRequest


_sns_client = boto3.client("sns")
logger = logging.getLogger(__file__)


def queue_upload_event_for_processing(upload_event):
	"""This method is used when UploadEvents are initially created.
	However it can also be used to requeue an UploadEvent to be
	processed again if an error was detected downstream that has now been fixed.
	"""
	topic_arn = settings.SNS_PROCESS_UPLOAD_EVENT_TOPIC
	message = {"upload_event_id": str(upload_event.id)}

	success = True
	try:
		response = _sns_client.publish(
			TopicArn=topic_arn,
			Message=json.dumps({"default": json.dumps(message)}),
			MessageStructure="json"
		)
	except Exception as e:
		error_handler(e)
		success = False
	else:
		message_id = response["MessageId"]

		try:
			UploadEventProcessingRequest.objects.create(
				upload_event = upload_event,
				sns_topic_arn = topic_arn,
				sns_message_id = message_id
			)
		except Exception as e:
			error_handler(e)
			success = False

		return message_id

	finally:
		influx_metric("queue_upload_event_for_processing",
			fields = {"value":1},
			timestamp = now(),
			tags={
				"success": success,
				"is_running_as_lambda": settings.IS_RUNNING_AS_LAMBDA,
			}
		)
