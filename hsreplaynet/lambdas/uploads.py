import logging, json
from base64 import b64decode
from web.models import *
from django.utils.timezone import now
from django.core.files.base import ContentFile

logging.getLogger('boto').setLevel(logging.WARN)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def _raw_log_upload_handler(event, context):
	query_params_json = event['query_parameters']
	params = json.loads(query_params_json)
	logger.info("Query Params: %s" % str(params))

	required_params = ('game_server_address', 'game_server_port', 'game_server_game_id')
	for p in required_params:
		if p not in params:
			raise ValidationError("The query parameter '%s' is required but was not found." % p)

	b64encoded_log = event['body']
	raw_log = b64decode(b64encoded_log)
	logger.info("*** Raw Log Data ***\n%s" % raw_log)

	api_key = event['x-hsreplay-api-key']
	upload_token = event['x-hsreplay-upload-token']

	raw_log_upload_record = SingleGameRawLogUpload()
	# Model fileds populated in the following section
	raw_log_upload_record.upload_token = SingleSiteUploadToken.objects.filter(token=upload_token).first()
	raw_log_upload_record.game_server_address = params.get('game_server_address')
	raw_log_upload_record.game_server_port = params.get('game_server_port')
	raw_log_upload_record.game_server_game_id = params.get('game_server_game_id')
	raw_log_upload_record.game_server_reconnecting = params.get('game_server_reconnecting')
	raw_log_upload_record.game_server_client_id = params.get('game_server_client_id')
	raw_log_upload_record.game_server_spectate_key = params.get('game_server_spectate_key')

	raw_log_upload_record.upload_timestamp = now()

	if 'match_start_timestamp' in params:
		match_start_timestamp = params.get('match_start_timestamp')
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
	raw_log_upload_record.hearthstone_build = params.get('hearthstone_build')
	raw_log_upload_record.game_type = params.get('game_type')
	raw_log_upload_record.is_spectated_game = params.get('is_spectated_game')
	raw_log_upload_record.friendly_player_id = params.get('friendly_player_id')
	raw_log_upload_record.scenario_id = params.get('scenario_id')
	raw_log_upload_record.player_1_rank = params.get('player_1_rank')
	raw_log_upload_record.player_1_legend_rank = params.get('player_1_legend_rank')
	raw_log_upload_record.player_1_deck_list = params.get('player_1_deck_list')
	raw_log_upload_record.player_2_rank = params.get('player_2_rank')
	raw_log_upload_record.player_2_legend_rank = params.get('player_2_legend_rank')
	raw_log_upload_record.player_2_deck_list = params.get('player_2_deck_list')

	try:
		raw_log_upload_record.full_clean()
		raw_log_upload_record.save()
	except ValidationError as e:
		# If we have a validation error we don't continue because it's most likely the result of malformed client requests.
		logger.exception(e)
		raise e

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
		result = str(replay.id)
	else:
		# Parsing failed so notify the uploader that there will be a delay
		result = "Upload succeeded, however there was a problem generating the replay. The replay will be available shortly."

	return result
