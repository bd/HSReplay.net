import json
import logging
import tempfile
from base64 import b64decode
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.timezone import now
from rest_framework.test import APIRequestFactory
from hsreplaynet import instrumentation
from hsreplaynet.uploads.models import UploadEvent, UploadEventType
from hsreplaynet.uploads.processing import queue_upload_event_for_processing
from hsreplaynet.api.views import UploadEventViewSet
from hsreplaynet.games.processing import process_upload_event


logging.getLogger("boto").setLevel(logging.WARN)
logger = logging.getLogger(__file__)
time_logger = logging.getLogger("TIMING")
logger.setLevel(logging.INFO)


@instrumentation.sentry_aware_handler
@instrumentation.influx_function_incovation_gauge
def create_power_log_upload_event_handler(event, context):
	"""
	A handler for creating UploadEvents via Lambda.
	"""
	handler_start = now()
	with instrumentation.influx_timer("create_power_log_upload_event_handler_duration_ms",
		timestamp=handler_start,
		is_running_as_lambda=settings.IS_RUNNING_AS_LAMBDA):

		try:
			logger.info("*** Event Data (excluding the body content) ***")
			for k, v in event.items():
				if k != "body":
					logger.info("%s: %s" % (k, v))

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

			query_params = event.get("query")
			query_params["file"] = power_log_file
			query_params["type"] = int(UploadEventType.POWER_LOG)

			factory = APIRequestFactory()
			request = factory.post(path, query_params, **headers)
			middleware = SessionMiddleware()
			middleware.process_request(request)

			view = UploadEventViewSet.as_view({'post': 'create'})
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



@instrumentation.sentry_aware_handler
@instrumentation.influx_function_incovation_gauge
def process_upload_event_handler(event, context):
	"""
	This handler is triggered by SNS whenever someone
	publishes a message to the SNS_PROCESS_UPLOAD_EVENT_TOPIC.
	"""

	handler_start = now()
	with instrumentation.influx_timer("process_upload_event_handler_duration_ms",
		timestamp=handler_start,
		is_running_as_lambda=settings.IS_RUNNING_AS_LAMBDA):

		logger.info("Received event: " + json.dumps(event, indent=2))
		message = json.loads(event['Records'][0]['Sns']['Message'])
		logger.info("From SNS: " + str(message))
		upload_event_id = message["upload_event_id"]
		logger.info("Upload Event ID: %s" % upload_event_id)

		try:
			game_upload = UploadEvent.objects.get(id=upload_event_id)
		except UploadEvent.DoesNotExist as e:
			instrumentation.error_handler(e)
		else:
			# TODO: Invoke downstream processing here.
			logger.info("UploadEvent's initial status is: %s" % str(game_upload.status))
			process_upload_event(game_upload)
			logger.info("UploadEvent's status after processing is: %s" % str(game_upload.status))
