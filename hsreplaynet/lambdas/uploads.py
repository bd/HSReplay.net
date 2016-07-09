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


@instrumentation.lambda_handler
def create_power_log_upload_event_handler(event, context):
	"""
	A handler for creating UploadEvents via Lambda.
	"""
	logger = logging.getLogger('hsreplaynet.lambdas.create_power_log_upload_event_handler')

	try:
		event_data = ", ".join("%s=%r" % (k, v) for k, v in event.items() if k != "body")
		logger.info("Event Data (excluding body): %s", event_data)

		body = b64decode(event.get("body"))
		instrumentation.influx_metric("raw_power_log_upload_num_bytes", {"size": len(body)})

		power_log_file = tempfile.NamedTemporaryFile(mode="r+b", suffix=".log")
		power_log_file.write(body)
		power_log_file.flush()
		power_log_file.seek(0)

		path = event.get("path")

		headers = event.get("headers")
		headers["HTTP_X_FORWARDED_FOR"] = event.get("source_ip")
		headers["HTTP_AUTHORIZATION"] = headers["Authorization"]
		headers["HTTP_X_API_KEY"] = headers.get("X-Api-Key")

		query_params = event.get("query")
		query_params["file"] = power_log_file
		query_params["type"] = int(UploadEventType.POWER_LOG)

		factory = APIRequestFactory()
		request = factory.post(path, query_params, **headers)
		middleware = SessionMiddleware()
		middleware.process_request(request)

		view = UploadEventViewSet.as_view({"post": "create"})
		response = view(request)
		response.render()
		logger.info("Response (code=%r): %s" % (response.status_code, response.content))

	except Exception as e:
		logger.exception(e)
		instrumentation.error_handler(e)
		raise Exception(json.dumps({
			"result_type": "SERVER_ERROR",
		}))

	else:
		if response.status_code == 201:
			# Extract the upload_event from the response, and queue it for downstream processing.
			try:
				upload_event_id = response.data["id"]
				queue_upload_event_for_processing(upload_event_id)
			except Exception as e:
				logger.exception(e)
				instrumentation.error_handler(e)
				raise Exception(json.dumps({
					"result_type": "SERVER_ERROR",
				}))

			return {
				"result_type": "SUCCESS",
				"body": response.content,
			}

		elif str(response.status_code).startswith("4"):
			raise Exception(json.dumps({
				"result_type": "VALIDATION_ERROR",
				"body": response.content
			}))

		else:
			# We should never reach this block
			raise Exception(json.dumps({
				"result_type": "SERVER_ERROR",
				"response_code": response.status_code,
				"response_content": response.content,
			}))


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
