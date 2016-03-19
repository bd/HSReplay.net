from django.test import TestCase
from web.models import *
from django.core.urlresolvers import reverse


class TestSingleSiteTokenRequest(TestCase):

	def setUp(self):
		super().setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)

	def test_request_upload_token(self):
		headers = {'x-hsreplay-api-key': self.upload_agent.api_key}
		response = self.client.post(reverse('generate_single_site_upload_token'), **headers)
		self.assertEqual(response.status_code, 201)

	def test_get_raises_not_allowed(self):
		headers = {'x-hsreplay-api-key': self.upload_agent.api_key}
		response = self.client.get(reverse('generate_single_site_upload_token'), **headers)
		self.assertEqual(response.status_code, 405)

	def test_missing_api_key_raises_401(self):
		response = self.client.post(reverse('generate_single_site_upload_token'))
		self.assertEqual(response.status_code, 401)