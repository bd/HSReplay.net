import requests
from django.core.urlresolvers import reverse
from django.test import LiveServerTestCase
from hsreplaynet.test.base import TestDataConsumerMixin
from web.models import *


class ReplayUploadTests(LiveServerTestCase, TestDataConsumerMixin):
	def setUp(self):
		super().setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@testagent.example.org",
			website="http://testagent.example.org"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent=self.upload_agent)
		self.server_url = self.live_server_url + reverse("replay_upload_view_v1")

	def test_replay_xml_upload_without_credentials(self):
		with open(self.replay_file_path("hslog.xml")) as xml_file:
			original_xml_data = xml_file.read()

			response = requests.post(self.server_url, data=original_xml_data.encode("utf-8"))
			self.assertEqual(response.status_code, 201)

			json = response.json()
			self.assertTrue("replay_uuid" in json)

	def test_replay_xml_upload_with_credentials(self):
		with open(self.replay_file_path("hslog.xml")) as xml_file:
			original_xml_data = xml_file.read()

			headers = {
				"x-hsreplay-api-key": str(self.upload_agent.api_key),
				"x-hsreplay-upload-token": str(self.token.token),
			}

			response = requests.post(
				self.server_url,
				data=original_xml_data.encode("utf-8"),
				headers=headers
			)
			self.assertEqual(response.status_code, 201)

			json = response.json()
			self.assertTrue("replay_uuid" in json)

			uploads = HSReplaySingleGameFileUpload.objects.filter(upload_token=self.token)
			self.assertEqual(uploads.count(), 1)
