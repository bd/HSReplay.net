import logging, json
from base64 import b64decode
from web.models import *
from django.utils.timezone import now
from django.core.files.base import ContentFile
import botocore.session

logging.getLogger('boto').setLevel(logging.WARN)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def _raw_log_upload_handler(event, context):
	logger.info("*** Event Data (excluding the body content) ***")
	for k,v in event.items():
		if k != 'body':
			logger.info("%s: %s" % (k, v))

	# Debug logging for Boto connection
	logger.info("Boto Credentials: %s" % str(botocore.session.get_session().get_credentials()))

	b64encoded_log = event['body']
	raw_log = b64decode(b64encoded_log)

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

	if 'match_start_timestamp' in event and len(event.get('match_start_timestamp')):
		match_start_timestamp = event.get('match_start_timestamp')
		if match_start_timestamp[-3] == ":":
			prefix, suffix = match_start_timestamp.rsplit(":", 1)
			match_start_timestamp = prefix + suffix

			# Now remove one degree of precision from microseconds
			prefix, suffix = match_start_timestamp.rsplit(".", 1)
			match_start_timestamp = prefix + '.' + suffix[:6] + suffix[-5:]

		raw_log_upload_record.match_start_timestamp = datetime.strptime(match_start_timestamp,'%Y-%m-%dT%H:%M:%S.%f%z')
	else:
		raw_log_upload_record.match_start_timestamp = raw_log_upload_record.upload_timestamp

	raw_log_upload_record.log.save('Power.log', ContentFile(raw_log), save=False)

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
	except ValidationError as e:
		# If we have a validation error we don't continue because it's most likely the result of malformed client requests.
		logger.exception(e)
		raise e

	logger.info("**** RAW LOG SUCCESSFULLY SAVED ****")
	logger.info("Raw Log Record ID: %s" % raw_log_upload_record.id)

	replay = None
	try:
		#Attempt parsing....
		replay = GameReplayUpload.objects.create_from_raw_log_upload(raw_log_upload_record)
	except Exception as e:
		# Even if parsing fails we don't return an error to the user because it's likely a problem that we can solve and
		# then reprocess the raw log file afterwords.
		logger.exception(e)

	result = None
	if replay:
		#Parsing succeeded so return the UUID of the replay.
		logger.info("Parsing Succeeded! Replay is %s turns, and has ID: %s" % (str(replay.global_game.num_turns), str(replay.id)))
		result = str(replay.id)
	else:
		logger.error("Parsing Failed!")
		# Parsing failed so notify the uploader that there will be a delay
		result = "Upload succeeded, however there was a problem generating the replay. The replay will be available shortly."

	return result
