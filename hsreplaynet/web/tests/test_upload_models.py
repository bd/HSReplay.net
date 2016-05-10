from django.test import TestCase
from web import models
from django.utils.timezone import now
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from cards.models import Card
from test.base import TestDataConsumerMixin
import logging
import pytz
from hearthstone.enums import BnetGameType
from hsreplay.utils import pretty_xml

logger = logging.getLogger(__name__)


# We patch S3Storage because we don't want to be interacting with S3 in unit tests
# You can temporarily comment out the @patch line to run the test in "integration mode" against S3. It should pass.
@patch('storages.backends.s3boto.S3BotoStorage', FileSystemStorage)
class ReplayUploadTests(TestCase, TestDataConsumerMixin):

	def setUp(self):
		super().setUp()
		self.log_data_fixture = self.get_raw_log_fixture_for_random_innkeeper_match()
		self.log_data = self.log_data_fixture['raw_log']

		self.thirty_card_deck = ['OG_249', 'CS2_147', 'EX1_620', 'FP1_019', 'AT_029', 'CS2_065', 'AT_070', 'OG_121', 'OG_290', 'GVG_038',
								'AT_133', 'EX1_023', 'FP1_014', 'OG_337', 'CS2_189', 'AT_066', 'AT_034', 'EX1_250', 'OG_330', 'AT_130',
								'GVG_081', 'OG_045', 'EX1_371', 'GVG_002', 'NEW1_026', 'EX1_405', 'OG_221', 'EX1_250', 'OG_330', 'AT_130']
		Card.objects.get_valid_deck_list_card_set = MagicMock(return_value=self.thirty_card_deck.copy())

		self.upload_agent = models.UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)
		self.token = models.SingleSiteUploadToken.objects.create(requested_by_upload_agent = self.upload_agent)

		# Set the timezone to something other than UTC to make sure it's being handled correctly
		self.upload_date = now().astimezone(pytz.timezone('Europe/Moscow'))

		self.upload = models.SingleGameRawLogUpload(upload_timestamp = self.upload_date,
												   match_start_timestamp = self.upload_date,
												   upload_token = self.token)

	def test_save_read_delete(self):

		self.upload.log.save('Power.log', ContentFile(self.log_data), save=False)
		self.upload.save()

		# Now we retrieve an instance to confirm that we can retrieve the data from S3
		db_record = models.SingleGameRawLogUpload.objects.get(id = self.upload.id)
		self.assertEqual(db_record.log.read(), self.log_data)

		db_record.delete()

	def test_validators(self):
		# This full_clean() should not throw an exception
		self.upload.log.save('Power.log', ContentFile(self.log_data), save=False)
		self.upload.player_1_deck_list = ",".join(self.thirty_card_deck)
		self.upload.full_clean()

		with self.assertRaises(ValidationError):
			self.upload.player_1_rank = 10
			self.upload.player_1_legend_rank = 1010
			self.upload.full_clean()

		with self.assertRaises(ValidationError):
			deck_with_invalid_card = self.thirty_card_deck.copy()[:-1]
			deck_with_invalid_card.append('AT_')
			self.upload.player_1_deck_list = ",".join(deck_with_invalid_card)
			self.upload.full_clean()

		with self.assertRaises(ValidationError):
			deck_with_too_few_cards = self.thirty_card_deck.copy()[0:22]
			self.upload.player_1_deck_list = ",".join(deck_with_too_few_cards)
			self.upload.full_clean()

	def test_generate_replay_element_tree(self):
		self.upload.log.save('Power.log', ContentFile(self.log_data), save=False)
		self.upload.player_1_deck_list = ",".join(self.thirty_card_deck)
		self.upload.player_1_rank = 18
		self.upload.match_type = int(BnetGameType.BGT_RANKED_STANDARD)

		replay = self.upload._generate_replay_element_tree()
		game_element = replay.find("Game")
		self.assertEqual(game_element.get("type"), str(self.upload.match_type))

		players = game_element.findall("Player")
		player_one = players[0]
		self.assertEqual(player_one.get("rank"), str(self.upload.player_1_rank))


		replay_xml = pretty_xml(replay)



