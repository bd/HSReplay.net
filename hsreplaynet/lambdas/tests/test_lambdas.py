from base64 import b64encode
from hsreplaynet.test.base import (
	TestDataConsumerMixin, CardDataBaseTest, create_agent_and_token
)
from hsreplaynet.web.models import GameReplayUpload
from ..uploads import _raw_log_upload_handler


class TestRawLogUploadHandler(CardDataBaseTest, TestDataConsumerMixin):
	def setUp(self):
		super().setUp()
		self.agent, self.token = create_agent_and_token()


	def test_basic_upload(self):
		self.log_data_fixture = self.get_raw_log_fixture_for_random_innkeeper_match()
		self.log_data = self.log_data_fixture["raw_log"]

		event = {
			"game_server_address": "12.130.246.55",
			"game_server_port": "3724",
			"game_server_game_id": "11927693",
			"game_server_reconnecting": "False",
			"game_server_client_id": "3850766",
			"game_server_spectate_key": "GnMGpi",
			"match_start_timestamp": "2016-05-10T17:10:06.4923855+02:00",
			"hearthstone_build": "10956",
			"game_type": "2",
			"is_spectated_game": "False",
			"friendly_player_id": "1",
			"player_1_rank": "18",
			"player_2_rank": "",
			"body": b64encode(self.log_data),
			"x-hsreplay-api-key": str(self.agent.api_key),
			"x-hsreplay-upload-token": str(self.token),
		}

		result = _raw_log_upload_handler(event, self.get_mock_context())
		print(result["replay_uuid"])
		replay = GameReplayUpload.objects.get(id=result["replay_uuid"])
		self.assertIsNotNone(replay)
