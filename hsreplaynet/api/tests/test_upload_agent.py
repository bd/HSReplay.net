import json
from django.test import TestCase
from hsreplaynet.test.base import create_agent_and_token


class TestAuthTokenRequest(TestCase):
	def setUp(self):
		super().setUp()
		self.agent, self.token = create_agent_and_token()
		self.url = "/api/v1/tokens/"

	def test_request_upload_token(self):
		data = json.dumps({"api_key": str(self.agent.api_key)})
		print("posting %r" % (data))
		response = self.client.post(self.url, content_type="application/json", data=data)
		self.assertEqual(response.status_code, 201)

	def test_get_raises_not_allowed(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 405)

	def test_missing_api_key_raises_400(self):
		response = self.client.post(self.url)
		self.assertEqual(response.status_code, 400)
