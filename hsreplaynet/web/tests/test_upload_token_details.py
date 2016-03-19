from django.test import TestCase
from web.models import *
from django.core.urlresolvers import reverse
import json


class TestUploadTokenDetails(TestCase):

	def setUp(self):
		super().setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent = self.upload_agent)
		self.headers = {'x-hsreplay-api-key': str(self.upload_agent.api_key)}

	def test_get_upload_token_details(self):
		attachment_url = reverse('upload_token_details_view', kwargs={'single_site_upload_token': str(self.token.token)})
		response = self.client.get(attachment_url, **self.headers)
		token_details = json.loads(response.content.decode("utf-8"))

		self.assertTrue("replays_are_public" in token_details)

	def test_modify_replay_visibility(self):
		attachment_url = reverse('upload_token_details_view', kwargs={'single_site_upload_token': str(self.token.token)})
		body = json.dumps({
			"replays_are_public": True
		})
		put_response = self.client.put(attachment_url, data = body, **self.headers)
		self.assertEqual(put_response.status_code, 200)

		get_response = self.client.get(attachment_url, **self.headers)
		token_details = json.loads(get_response.content.decode("utf-8"))
		self.assertTrue(token_details["replays_are_public"])
