from django.test import TestCase
from web.models import *
from unittest import skip
from django.utils.timezone import now
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from cards.models import Card
from test.base import TestDataConsumerMixin
import logging
from hearthstone.enums import BnetGameType
from hsreplay.utils import pretty_xml
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


# We patch S3Storage because we don't want to be interacting with S3 in unit tests
# You can temporarily comment out the @patch line to run the test in "integration mode" against S3. It should pass.
@patch('storages.backends.s3boto.S3BotoStorage', FileSystemStorage)
class CreateReplayFromRawLogTests(TestCase, TestDataConsumerMixin):
	fixtures = ['cards_filtered.json', ]

	def setUp(self):
		super().setUp()
		self.log_data_fixture = self.get_raw_log_fixture_for_random_innkeeper_match()
		self.log_data = self.log_data_fixture['raw_log']

		self.thirty_card_deck = ['AT_004', 'AT_004', 'AT_006', 'AT_006', 'AT_019', 'CS2_142', 'CS2_142', 'CS2_146', 'CS2_146', 'CS2_161',
								'CS2_161', 'CS2_169', 'CS2_169', 'CS2_181', 'CS2_181', 'CS2_189', 'CS2_189', 'CS2_200', 'CS2_200', 'AT_130',
								'GVG_081', 'CS2_213', 'EX1_371', 'GVG_002', 'NEW1_026', 'EX1_405', 'CS2_213', 'EX1_250', 'CS2_222', 'AT_130']
		Card.objects.get_valid_deck_list_card_set = MagicMock(return_value=self.thirty_card_deck.copy())

		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent = self.upload_agent)

		# Set the timezone to something other than UTC to make sure it's being handled correctly
		self.upload_date = self.log_data_fixture['upload_date']

		self.upload = SingleGameRawLogUpload(upload_timestamp = self.upload_date,
												   match_start_timestamp = self.upload_date,
												   upload_token = self.token)

	def test_create_replay_from_raw_log(self):

		self.upload.log.save('Power.log', ContentFile(self.log_data), save=False)
		self.upload.player_1_deck_list = ",".join(self.thirty_card_deck)
		self.upload.player_1_rank = 18
		self.upload.match_type = int(BnetGameType.BGT_RANKED_STANDARD)
		self.upload.save()

		replay = GameReplayUpload.objects.create_from_raw_log_upload(self.upload)
		self.assertEqual(replay.upload_token, self.token)
		self.assertEqual(replay.upload_timestamp, self.upload_date)
		self.assertEqual(replay.raw_log, self.upload)

		self.assertEqual(replay.player_one_name, self.log_data_fixture['player_one_name'])
		self.assertEqual(replay.player_two_name, self.log_data_fixture['player_two_name'])


		replay_xml = replay.replay_xml.read()
		replay_tree = ET.fromstring(replay_xml)
		self.assertIsNotNone(replay_tree.find("Game"))
		self.assertEqual(len(list(replay_tree.iter("Player"))), 2)
		self.assertEqual(replay.hsreplay_version, hsreplay_version)

		player_one_starting_deck = replay.player_one_starting_deck_list
		expected_starting_deck = Deck.objects.create_from_id_list(self.thirty_card_deck)
		self.assertEqual(player_one_starting_deck.card_id_list(), expected_starting_deck.card_id_list())

		self.assertIsNotNone(replay.global_game)
		global_game = replay.global_game
		self.assertEqual(global_game.bnet_region_id, self.log_data_fixture['bnet_region_id'])
		self.assertEqual(global_game.match_start_timestamp, self.log_data_fixture['match_start_timestamp'])

		# There might be an issue with hslog.parser.parse_timestamp() rolling over the match date when it doesn't need to.
		# self.assertEqual(global_game.match_end_timestamp, self.log_data_fixture['match_end_timestamp'])

		self.assertEqual(global_game.player_one_battlenet_id, self.log_data_fixture['player_one_battlenet_id'])
		self.assertEqual(global_game.player_one_starting_hero_id, self.log_data_fixture['player_one_starting_hero_id'])
		self.assertEqual(global_game.player_one_starting_hero_class, self.log_data_fixture['player_one_starting_hero_class'])
		self.assertEqual(global_game.player_one_final_state, self.log_data_fixture['player_one_final_state'])

		self.assertEqual(global_game.player_two_battlenet_id, self.log_data_fixture['player_two_battlenet_id'])
		self.assertEqual(global_game.player_two_starting_hero_id, self.log_data_fixture['player_two_starting_hero_id'])
		self.assertEqual(global_game.player_two_starting_hero_class, self.log_data_fixture['player_two_starting_hero_class'])
		self.assertEqual(global_game.player_two_final_state, self.log_data_fixture['player_two_final_state'])

		self.assertEqual(global_game.num_turns, self.log_data_fixture['num_turns'])
		self.assertEqual(global_game.num_entities, self.log_data_fixture['num_entities'])

	@skip
	def test_uploading_duplicate_replays_are_rejected(self):
		pass

	@skip
	def test_uploading_two_different_replay_povs_share_a_global_game(self):
		pass
