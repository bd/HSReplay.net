import json
import logging
import tempfile
from base64 import b64decode
from dateutil.parser import parse as datetime_parse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.timezone import now
from hsreplaynet.instrumentation import error_handler, influx_metric, influx_timer
from hsreplaynet.api.models import AuthToken
from hsreplaynet.uploads.models import GameUpload, GameUploadType, GameUploadStatus
from hsreplaynet.web.models import GameReplayUpload, SingleGameRawLogUpload
from hsreplaynet.uploads.processing import queue_upload_event_for_processing
from hsreplaynet.utils import _time_elapsed, _reset_time_elapsed
from rest_framework.test import APIRequestFactory
from hsreplaynet.api.views import GameUploadViewSet
from django.contrib.sessions.middleware import SessionMiddleware
from hsreplaynet.games.models import process_upload_event

logging.getLogger("boto").setLevel(logging.WARN)
logger = logging.getLogger(__file__)
time_logger = logging.getLogger("TIMING")
logger.setLevel(logging.INFO)


def create_power_log_upload_event_handler(event, context):
	"""
	A handler for creating UploadEvents via Lambda.
	"""
	handler_start = now()
	with influx_timer("create_power_log_upload_event_handler_duration_ms",
					  timestamp=handler_start,
					  is_running_as_lambda=settings.IS_RUNNING_AS_LAMBDA):

		try:
			logger.info("*** Event Data (excluding the body content) ***")
			for k, v in event.items():
				if k != "body":
					logger.info("%s: %s" % (k, v))

			body = b64decode(event.get("body"))
			power_log_file = tempfile.NamedTemporaryFile(mode="r+b",suffix='.log')
			power_log_file.write(body)
			power_log_file.flush()
			power_log_file.seek(0)

			path = event.get("path")

			headers = event.get("headers")
			headers["HTTP_X_FORWARDED_FOR"] = event.get("source_ip")
			headers["HTTP_AUTHORIZATION"] = headers["Authorization"]

			query_params = event.get("query")
			query_params["file"] = power_log_file
			query_params["type"] = int(GameUploadType.POWER_LOG)

			factory = APIRequestFactory()
			request = factory.post(path, query_params, **headers)
			middleware = SessionMiddleware()
			middleware.process_request(request)

			view = GameUploadViewSet.as_view({'post': 'create'})
			response = view(request)
			response.render()
			logger.info("Response Code: %s Response Content: %s" % (response.status_code, response.content))

			if str(response.status_code).startswith("4"):
				return {
					"result_type": "VALIDATION_ERROR",
					"body": response.content
				}

			elif response.status_code == 201:

				# Extract the upload_event from the response, and queue it for downstream processing.
				upload_event_id = response.data["id"]
				queue_upload_event_for_processing(upload_event_id)

				return {
					"result_type" : "SUCCESS",
					"body" : response.content
				}

			else:
				# We should never reach this block
				return {
					"result_type": "SERVER_ERROR",
					"response_code": response.status_code,
					"response_content": response.content
				}

		except Exception as e:
			logger.exception(e)
			error_handler(e)
			return {
				"result_type" : "SERVER_ERROR"
			}


def raw_log_upload_handler(event, context):
	# If an exception is thrown we must translate it into a string that the API Gateway
	# can translate into the appropriate HTTP Response code and message.
	handler_start = now()
	with influx_timer("raw_log_upload_handler_duration_ms", timestamp=handler_start, is_running_as_lambda=settings.IS_RUNNING_AS_LAMBDA):
		event['_handler_start'] = handler_start
		result = None
		try:
			result = _raw_log_upload_handler(event, context)
			logger.info("Handler returned the string: %s" % (result))
		except ValidationError as e:
			# TODO: Provide additional detailed messaging for ValidationErrors
			error_handler(e)
			result = {
				"result": "ERROR",
				"replay_available": False,
				"msg": str(e),
				"replay_uuid": "",
			}

		except Exception as e:
			error_handler(e)
			result = {
				"result": "ERROR",
				"replay_available": False,
				"msg": str(e),
				"replay_uuid": "",
			}

		return result


def process_upload_event_handler(event, context):
	"""
	This handler is triggered by SNS whenever someone
	publishes a message to the SNS_PROCESS_UPLOAD_EVENT_TOPIC.
	"""

	handler_start = now()
	with influx_timer("process_upload_event_handler_duration_ms",
					  timestamp=handler_start,
					  is_running_as_lambda=settings.IS_RUNNING_AS_LAMBDA):

		logger.info("Received event: " + json.dumps(event, indent=2))
		message = json.loads(event['Records'][0]['Sns']['Message'])
		logger.info("From SNS: " + str(message))
		upload_event_id = message["upload_event_id"]
		logger.info("Upload Event ID: %s" % upload_event_id)

		try:
			game_upload = GameUpload.objects.get(id=upload_event_id)
		except GameUpload.DoesNotExist as e:
			error_handler(e)
		else:
			# TODO: Invoke downstream processing here.
			logger.info("GameUpload's initial status is: %s" % str(game_upload.status))
			process_upload_event(game_upload)
			logger.info("GameUpload's status after processing is: %s" % str(game_upload.status))


def create_upload_event_handler(event, context):
	"""
	A handler for creating UploadEvents via Lambda.
	"""
	_reset_time_elapsed()
	time_logger.info("TIMING: %s - create_upload_event_handler start." % _time_elapsed())
	logger.info("*** Event Data (excluding the body content) ***")

	meta_data = {}
	for k, v in event.items():
		if k != "body":
			logger.info("%s: %s" % (k, v))
			meta_data[k] = v

	# TODO: Port validators from RawLogUpload and run them in case we need to return a validation error.
	try:
		b64encoded_log = event["body"]
		body_data = b64decode(b64encoded_log)
		time_logger.info("TIMING: %s - After Base64 decoding." % _time_elapsed())

		api_key = event["x-hsreplay-api-key"]
		logger.info("Upload submitted with API Key: %s" % api_key)
		token = event["x-hsreplay-upload-token"]
		logger.info("Upload submitted with Upload Token: %s" % token)

		upload_event_type = GameUploadType.POWER_LOG
		#TODO: We need to extract the clients intended upload type from the event metadata.

		upload_event = GameUpload.objects.create(
			token = AuthToken.objects.filter(key=token).first(),
			type = upload_event_type,
			upload_up = event.get("source_ip"),
			status = GameUploadStatus.PROCESSING,
			meta_data = json.dumps(meta_data),
			file = ContentFile(body_data, name=upload_event_type.name)
		)

		# Publish a message to SNS to queue the upload_event for downstream processing.
		queue_upload_event_for_processing(upload_event)

	except Exception as e:
		error_handler(e)
		time_logger.info("TIMING: %s - create_upload_event_handler Finished. Returning FAILURE." % _time_elapsed())
		return {"result": "FAILURE", "upload_event_id": ""}
	else:
		time_logger.info("TIMING: %s - create_upload_event_handler Finished. Returning SUCCESS." % _time_elapsed())
		return {"result": "SUCCESS", "upload_event_id": str(upload_event.id)}


def _raw_log_upload_handler(event, context):
	_reset_time_elapsed() # To cleanly reset when the same lambda runtime is used to process multiple uploads.
	time_logger.info("TIMING: %s - Upload handler start." % _time_elapsed())
	logger.info("*** Event Data (excluding the body content) ***")
	for k, v in event.items():
		if k != "body":
			logger.info("%s: %s" % (k, v))

	b64encoded_log = event["body"]
	raw_log = b64decode(b64encoded_log)
	time_logger.info("TIMING: %s - After Base64 decoding." % _time_elapsed())


	api_key = event["x-hsreplay-api-key"]
	logger.info("Upload submitted with API Key: %s" % api_key)
	token = event["x-hsreplay-upload-token"]
	logger.info("Upload submitted with Upload Token: %s" % token)

	raw_log_upload_record = SingleGameRawLogUpload()
	# Model fileds populated in the following section
	raw_log_upload_record.upload_token = AuthToken.objects.filter(key=token).first()

	if event.get("game_server_address"):
		raw_log_upload_record.game_server_address = event.get("game_server_address")

	if event.get("game_server_port"):
		raw_log_upload_record.game_server_port = int(event.get("game_server_port"))

	if event.get("game_server_game_id"):
		raw_log_upload_record.game_server_game_id = int(event.get("game_server_game_id"))

	if event.get("game_server_reconnecting", "").lower() == "true":
		raw_log_upload_record.game_server_reconnecting = True
	else:
		raw_log_upload_record.game_server_reconnecting = False

	if event.get("game_server_client_id"):
		raw_log_upload_record.game_server_client_id = int(event.get("game_server_client_id"))

	if event.get("game_server_spectate_key"):
		raw_log_upload_record.game_server_spectate_key = event.get("game_server_spectate_key")

	if '_handler_start' in event:
		raw_log_upload_record.upload_timestamp = event['_handler_start']
	else:
		raw_log_upload_record.upload_timestamp = now()

	influx_metric("raw_log_num_bytes",
				  fields={"value":len(raw_log)},
				  timestamp = raw_log_upload_record.upload_timestamp,
				  tags={"is_running_as_lambda": settings.IS_RUNNING_AS_LAMBDA})

	if event.get("match_start_timestamp"):
		match_start_timestamp_str = event.get("match_start_timestamp")
		match_start_timestamp = datetime_parse(match_start_timestamp_str)
		raw_log_upload_record.match_start_timestamp = match_start_timestamp
	else:
		raw_log_upload_record.match_start_timestamp = raw_log_upload_record.upload_timestamp

	raw_log_upload_record.log.save("Power.log", ContentFile(raw_log), save=False)
	time_logger.info("TIMING: %s - After raw_log_upload_record.log.save" % _time_elapsed())

	if event.get("hearthstone_build"):
		raw_log_upload_record.hearthstone_build = event.get("hearthstone_build")

	if event.get("game_type"):
		raw_log_upload_record.game_type = int(event.get("game_type"))

	if event.get("is_spectated_game") and event.get("is_spectated_game").lower() == "true":
		raw_log_upload_record.is_spectated_game = True
	else:
		raw_log_upload_record.is_spectated_game = False

	if event.get("friendly_player_id"):
		raw_log_upload_record.friendly_player_id = int(event.get("friendly_player_id"))

	if event.get("scenario_id"):
		raw_log_upload_record.scenario_id = int(event.get("scenario_id"))

	if event.get("player_1_rank"):
		raw_log_upload_record.player_1_rank = int(event.get("player_1_rank"))

	if event.get("player_1_legend_rank"):
		raw_log_upload_record.player_1_legend_rank = event.get("player_1_legend_rank")

	if event.get("player_1_deck_list"):
		raw_log_upload_record.player_1_deck_list = event.get("player_1_deck_list")

	if event.get("player_2_rank"):
		raw_log_upload_record.player_2_rank = int(event.get("player_2_rank"))

	if event.get("player_2_legend_rank"):
		raw_log_upload_record.player_2_legend_rank = int(event.get("player_2_legend_rank"))

	if event.get("player_2_deck_list"):
		raw_log_upload_record.player_2_deck_list = event.get("player_2_deck_list")

	try:
		raw_log_upload_record.full_clean()
		raw_log_upload_record.save()
		time_logger.info("TIMING: %s - After raw_log_upload_record.save()" % _time_elapsed())
	except ValidationError as e:
		# If we have a validation error we don't continue because it's most likely
		# the result of malformed client requests.
		error_handler(e)
		raise e

	logger.info("**** RAW LOG SUCCESSFULLY SAVED ****")
	logger.info("Raw Log Record ID: %s" % raw_log_upload_record.id)

	replay = None
	created = False
	try:
		# Attempt parsing....
		replay, created = GameReplayUpload.objects.get_or_create_from_raw_log_upload(raw_log_upload_record)
		time_logger.info("TIMING: %s - After GameReplayUpload.objects.get_or_create_from_raw_log_upload" % _time_elapsed())
	except Exception as e:
		# Even if parsing fails we don't return an error to the user
		# because it's likely a problem that we can solve and then
		# reprocess the raw log file afterwords.
		error_handler(e)

	result = {
		"result": "SUCCESS",
		"replay_available": False,
		"msg": "",
		"replay_uuid": ""
	}
	if replay:
		# Parsing succeeded so return the UUID of the replay.
		logger.info("Parsing Succeeded! Replay is %i turns, and has ID %r" % (
			replay.global_game.num_turns, replay.id)
		)
		if not created:
			logger.warn("This replay was determined to be a duplicate of an earlier upload. A new replay record did not need to be created.")
		result["replay_available"] = True
		result["replay_uuid"] = str(replay.id)
	else:
		logger.error("Parsing Failed!")
		# Parsing failed so notify the uploader that there will be a delay
		result["msg"] = "Upload succeeded, however there was a problem generating the replay. The replay will be available shortly."

	time_logger.info("TIMING: %s - About to send result." % _time_elapsed())
	return result
