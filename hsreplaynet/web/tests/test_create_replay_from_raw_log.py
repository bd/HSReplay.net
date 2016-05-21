from unittest import skip
from xml.etree import ElementTree
from hsreplaynet.test.base import CardDataBaseTest, TestDataConsumerMixin
from hsreplaynet.web.models import *


class CreateReplayFromRawLogTests(CardDataBaseTest, TestDataConsumerMixin):
	def setUp(self):
		super().setUp()

		self.log_data_fixture = self.get_raw_log_fixture_for_random_innkeeper_match()
		self.log_data = self.log_data_fixture["raw_log"]

		self.thirty_card_deck = [
			"AT_004", "AT_004", "AT_006", "AT_006", "AT_019", "CS2_142", "CS2_142", "CS2_146", "CS2_146", "CS2_161",
			"CS2_161", "CS2_169", "CS2_169", "CS2_181", "CS2_181", "CS2_189", "CS2_189", "CS2_200", "CS2_200", "AT_130",
			"GVG_081", "CS2_213", "EX1_371", "GVG_002", "NEW1_026", "EX1_405", "CS2_213", "EX1_250", "CS2_222", "AT_130"
		]

		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@testagent.example.org",
			website="http://testagent.example.org"
		)
		self.token = SingleSiteUploadToken.objects.create(upload_agent=self.upload_agent)

		# Set the timezone to something other than UTC to make sure it"s being handled correctly
		self.upload_date = self.log_data_fixture["upload_date"]
		self.upload = SingleGameRawLogUpload(
			upload_timestamp=self.upload_date,
			match_start_timestamp=self.upload_date,
			upload_token=self.token
		)

	def tearDown(self):
		for replay_upload in self.upload.replays.all():
			replay_upload.replay_xml.delete()

		self.upload.log.delete()

	def test_create_replay_from_raw_log(self):
		self.upload.log.save("Power.log", ContentFile(self.log_data), save=False)
		self.upload.player_1_deck_list = ",".join(self.thirty_card_deck)
		self.upload.player_1_rank = 18
		self.upload.match_type = BnetGameType.BGT_RANKED_STANDARD
		self.upload.save()

		replay, previously_existed = GameReplayUpload.objects.get_or_create_from_raw_log_upload(self.upload)
		self.assertEqual(replay.upload_token, self.token)
		self.assertEqual(replay.upload_timestamp, self.upload_date)
		self.assertEqual(replay.raw_log, self.upload)

		replay_xml = replay.replay_xml.read()
		replay_tree = ElementTree.fromstring(replay_xml)
		self.assertIsNotNone(replay_tree.find("Game"))
		self.assertEqual(len(list(replay_tree.iter("Player"))), 2)
		self.assertEqual(replay.hsreplay_version, hsreplay_version)

		self.assertIsNotNone(replay.global_game)
		global_game = replay.global_game
		self.assertEqual(global_game.match_start_timestamp, self.log_data_fixture["match_start_timestamp"])
		self.assertEqual(global_game.match_end_timestamp, self.log_data_fixture["match_end_timestamp"])

		self.assertEqual(global_game.num_turns, self.log_data_fixture["num_turns"])
		self.assertEqual(global_game.num_entities, self.log_data_fixture["num_entities"])
		self.assertEqual(str(global_game), "Nicodemus vs The Innkeeper")

	@skip
	def test_uploading_duplicate_replays_are_rejected(self):
		pass

	@skip
	def test_uploading_two_different_replay_povs_share_a_global_game(self):
		pass
