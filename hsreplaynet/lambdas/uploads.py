import logging, json
from base64 import b64decode
from web.models import *
from django.utils.timezone import now
from django.core.files.base import ContentFile
import dateutil.parser
from hsutils.performance import _time_elapsed

logging.getLogger('boto').setLevel(logging.WARN)
logger = logging.getLogger(__file__)
time_logger = logging.getLogger("TIMING")
logger.setLevel(logging.INFO)



def _raw_log_upload_handler(event, context):

	time_logger.info("TIMING: %s - Upload handler start." % _time_elapsed())
	logger.info("*** Event Data (excluding the body content) ***")
	for k,v in event.items():
		if k != 'body':
			logger.info("%s: %s" % (k, v))

	b64encoded_log = event['body']
	raw_log = b64decode(b64encoded_log)
	time_logger.info("TIMING: %s - After Base64 decoding." % _time_elapsed())

	api_key = event['x-hsreplay-api-key']
	logger.info("Upload submitted with API Key: %s" % api_key)
	upload_token = event['x-hsreplay-upload-token']
	logger.info("Upload submitted with Upload Token: %s" % upload_token)

	raw_log_upload_record = SingleGameRawLogUpload()
	# Model fileds populated in the following section
	raw_log_upload_record.upload_token = SingleSiteUploadToken.objects.filter(token=upload_token).first()

	if event.get('game_server_address'):
		raw_log_upload_record.game_server_address = event.get('game_server_address')

	if event.get('game_server_port'):
		raw_log_upload_record.game_server_port = int(event.get('game_server_port'))

	if event.get('game_server_game_id'):
		raw_log_upload_record.game_server_game_id = int(event.get('game_server_game_id'))

	if event.get('game_server_reconnecting') and event.get('game_server_reconnecting').lower() == 'true':
		raw_log_upload_record.game_server_reconnecting = True
	else:
		raw_log_upload_record.game_server_reconnecting = False

	if event.get('game_server_client_id'):
		raw_log_upload_record.game_server_client_id = int(event.get('game_server_client_id'))

	if event.get('game_server_spectate_key'):
		raw_log_upload_record.game_server_spectate_key = event.get('game_server_spectate_key')

	raw_log_upload_record.upload_timestamp = now()

	if event.get("match_start_timestamp"):
		match_start_timestamp_str = event.get("match_start_timestamp")
		match_start_timestamp = dateutil.parser.parse(match_start_timestamp_str)
		raw_log_upload_record.match_start_timestamp = match_start_timestamp
	else:
		raw_log_upload_record.match_start_timestamp = raw_log_upload_record.upload_timestamp

	raw_log_upload_record.log.save('Power.log', ContentFile(raw_log), save=False)
	time_logger.info("TIMING: %s - After raw_log_upload_record.log.save" % _time_elapsed())

	if event.get('hearthstone_build'):
		raw_log_upload_record.hearthstone_build = event.get('hearthstone_build')

	if event.get('game_type'):
		raw_log_upload_record.game_type = int(event.get('game_type'))

	if event.get('is_spectated_game') and event.get('is_spectated_game').lower() == 'true':
		raw_log_upload_record.is_spectated_game = True
	else:
		raw_log_upload_record.is_spectated_game = False

	if event.get('friendly_player_id'):
		raw_log_upload_record.friendly_player_id = int(event.get('friendly_player_id'))

	if event.get('scenario_id'):
		raw_log_upload_record.scenario_id = int(event.get('scenario_id'))

	if event.get('player_1_rank'):
		raw_log_upload_record.player_1_rank = int(event.get('player_1_rank'))

	if event.get('player_1_legend_rank'):
		raw_log_upload_record.player_1_legend_rank = event.get('player_1_legend_rank')

	if event.get('player_1_deck_list'):
		raw_log_upload_record.player_1_deck_list = event.get('player_1_deck_list')

	if event.get('player_2_rank'):
		raw_log_upload_record.player_2_rank = int(event.get('player_2_rank'))

	if event.get('player_2_legend_rank'):
		raw_log_upload_record.player_2_legend_rank = int(event.get('player_2_legend_rank'))

	if event.get('player_2_deck_list'):
		raw_log_upload_record.player_2_deck_list = event.get('player_2_deck_list')

	try:
		raw_log_upload_record.full_clean()
		raw_log_upload_record.save()
		time_logger.info("TIMING: %s - After raw_log_upload_record.save()" % _time_elapsed())
	except ValidationError as e:
		# If we have a validation error we don't continue because it's most likely the result of malformed client requests.
		logger.exception(e)
		raise e

	logger.info("**** RAW LOG SUCCESSFULLY SAVED ****")
	logger.info("Raw Log Record ID: %s" % raw_log_upload_record.id)

	replay = None
	created = False
	try:
		#Attempt parsing....
		replay, created = GameReplayUpload.objects.get_or_create_from_raw_log_upload(raw_log_upload_record)
		time_logger.info("TIMING: %s - After GameReplayUpload.objects.get_or_create_from_raw_log_upload" % _time_elapsed())
	except Exception as e:
		# Even if parsing fails we don't return an error to the user because it's likely a problem that we can solve and
		# then reprocess the raw log file afterwords.
		logger.exception(e)

	result = {
		"result" : "SUCCESS",
		"replay_available" : False,
		"msg" : "",
		"replay_uuid" : ""
	}
	if replay:
		#Parsing succeeded so return the UUID of the replay.
		logger.info("Parsing Succeeded! Replay is %s turns, and has ID: %s" % (str(replay.global_game.num_turns), str(replay.id)))
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
