import pytz
from django.test import TestCase
from django.utils.timezone import now
from hsreplaynet.test.base import TestDataConsumerMixin
from hsreplaynet.web.models import *


class ReplayUploadTests(TestCase, TestDataConsumerMixin):
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

		# Set the timezone to something other than UTC to make sure it's being handled correctly
		self.upload_date = now().astimezone(pytz.timezone("Europe/Moscow"))

		self.upload = SingleGameRawLogUpload(
			upload_timestamp=self.upload_date,
			match_start_timestamp=self.upload_date,
			upload_token=self.token
		)

	def tearDown(self):
		self.upload.log.delete()

	def test_save_read_delete(self):
		self.upload.log.save("Power.log", ContentFile(self.log_data), save=False)
		self.upload.save()

		# Now we retrieve an instance to confirm that we can retrieve the data from S3
		db_record = SingleGameRawLogUpload.objects.get(id=self.upload.id)
		self.assertEqual(db_record.log.read(), self.log_data)

		db_record.delete()

	def test_validators(self):
		# This full_clean() should not throw an exception
		self.upload.log.save("Power.log", ContentFile(self.log_data), save=False)
		self.upload.player_1_deck_list = ",".join(self.thirty_card_deck)
		self.upload.full_clean()

		with self.assertRaises(ValidationError):
			self.upload.player_1_rank = 10
			self.upload.player_1_legend_rank = 1010
			self.upload.full_clean()

		with self.assertRaises(ValidationError):
			deck_with_invalid_card = self.thirty_card_deck.copy()[:-1]
			deck_with_invalid_card.append("AT_")
			self.upload.player_1_deck_list = ",".join(deck_with_invalid_card)
			self.upload.full_clean()

		with self.assertRaises(ValidationError):
			deck_with_too_few_cards = self.thirty_card_deck.copy()[0:22]
			self.upload.player_1_deck_list = ",".join(deck_with_too_few_cards)
			self.upload.full_clean()
