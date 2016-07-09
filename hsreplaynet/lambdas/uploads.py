import json
import logging
import tempfile
from base64 import b64decode
from django.contrib.sessions.middleware import SessionMiddleware
from rest_framework.test import APIRequestFactory
from hsreplaynet.api.views import UploadEventViewSet
from hsreplaynet.uploads.models import UploadEvent, UploadEventType
from hsreplaynet.uploads.processing import queue_upload_event_for_processing
from hsreplaynet.utils import instrumentation


def create_fake_api_request(event, body, headers):
	"""
	Emulates an API request from the API gateway's data.
	"""
	file = tempfile.NamedTemporaryFile(mode="r+b", suffix=".log")
	file.write(body)
	file.flush()
	file.seek(0)

	data = event["query"]
	data["file"] = file
	data["type"] = int(UploadEventType.POWER_LOG)

	extra = {
		"HTTP_X_FORWARDED_FOR": event["source_ip"],
		"HTTP_AUTHORIZATION": headers["Authorization"],
		"HTTP_X_API_KEY": headers["X-Api-Key"],
	}

	factory = APIRequestFactory()
	request = factory.post(event["path"], data, **extra)
	SessionMiddleware().process_request(request)
	return request


@instrumentation.lambda_handler
def create_power_log_upload_event_handler(event, context):
	"""
	A handler for creating UploadEvents via Lambda.
	"""
	logger = logging.getLogger('hsreplaynet.lambdas.create_power_log_upload_event_handler')

	body = event.pop("body")
	headers = event.pop("headers")
	event_data = ", ".join("%s=%r" % (k, v) for k, v in event.items())
	logger.info("Event Data (excluding body): %s", event_data)
	logger.info("Headers: %r", headers)

	body = b64decode(body)
	instrumentation.influx_metric("raw_power_log_upload_num_bytes", {"size": len(body)})

	request = create_fake_api_request(event, body, headers)
	view = UploadEventViewSet.as_view({"post": "create"})

	try:
		response = view(request)
		response.render()
		logger.info("Response (code=%r): %s" % (response.status_code, response.content))

	except Exception as e:
		logger.exception(e)
		raise Exception(json.dumps({
			"result_type": "SERVER_ERROR",
			"body": str(e),
		}))

	if response.status_code != 201:
		result = {
			"result_type": "VALIDATION_ERROR",
			"status_code": response.status_code,
			"body": response.content,
		}
		raise Exception(json.dumps(result))

	# Extract the upload_event from the response and queue it for processing
	upload_event_id = response.data["id"]
	logger.info("Created upload event %r, queuing for processing", upload_event_id)
	queue_upload_event_for_processing(upload_event_id)

	return {
		"result_type": "SUCCESS",
		"body": response.content,
	}


@instrumentation.lambda_handler
def process_upload_event_handler(event, context):
	"""
	This handler is triggered by SNS whenever someone
	publishes a message to the SNS_PROCESS_UPLOAD_EVENT_TOPIC.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_upload_event_handler")

	event_data = ", ".join("%s=%r" % (k, v) for k, v in event.items())
	logger.info("Event Data: %s", event_data)
	message = json.loads(event["Records"][0]["Sns"]["Message"])
	logger.info("SNS message: %r", message)

	if "upload_event_id" not in message:
		raise RuntimeError("Missing upload_event_id in %r" % (message))

	# This should never raise DoesNotExist.
	# If it does, the previous lambda made a terrible mistake.
	upload = UploadEvent.objects.get(id=message["upload_event_id"])

	logger.info("Processing %r (status=%r)", upload, upload.status)
	upload.process()
	logger.info("Finished processing %r (status=%r)", upload, upload.status)
