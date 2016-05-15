import json
from base64 import b64encode
from unittest import skip
from unittest.mock import patch
from django.core.files.storage import FileSystemStorage
from lambdas.uploads import _raw_log_upload_handler
from test.base import CardDataBaseTest, TestDataConsumerMixin
from web.models import *
from django.conf import settings

# We patch S3Storage because we don't want to be interacting with S3 in unit tests
# You can temporarily comment out the @patch line to run the test in "integration mode" against S3. It should pass.
@patch(settings.DEFAULT_FILE_STORAGE, FileSystemStorage)
class TestRawLogUploadHandler(CardDataBaseTest, TestDataConsumerMixin):
	def setUp(self):
		super().setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@testagent.example.org",
			website="http://testagent.example.org"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent=self.upload_agent)

	def test_basic_upload(self):
		self.log_data_fixture = self.get_raw_log_fixture_for_random_innkeeper_match()
		self.log_data = self.log_data_fixture["raw_log"]

		event = {
			"game_server_address": "12.130.246.55",
			"game_server_port": "3724",
			"game_server_game_id" : "11927693",
			"game_server_reconnecting" : "False",
			"game_server_client_id" : "3850766",
			"game_server_spectate_key" : "GnMGpi",
			"match_start_timestamp" : "2016-05-10T17:10:06.4923855+02:00",
			"hearthstone_build" : "10956",
			"game_type": "2",
			"is_spectated_game" : "False",
			"friendly_player_id" : "1",
			"player_1_rank" : "18",
			"player_2_rank" : "",
			"body" : b64encode(self.log_data),
			"x-hsreplay-api-key" : str(self.upload_agent.api_key),
			"x-hsreplay-upload-token" : str(self.token.token)
		}

		context = {}

		replay_id = _raw_log_upload_handler(event, context)
		replay = GameReplayUpload.objects.get(id=replay_id)
		self.assertIsNotNone(replay)
