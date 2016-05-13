from urllib.parse import urlparse, parse_qs
from allauth.socialaccount.models import SocialApp
from allauth.tests import MockedResponse, mocked_response
from allauth.utils import get_current_site
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from web.models import UploadAgentAPIKey, SingleSiteUploadToken


class TestBattleNetOAuth(TestCase):
	def setUp(self):
		app = SocialApp.objects.create(
			provider="battlenet",
			name="battlenet",
			client_id="app123id",
			key="battlenet",
			secret="dummy"
		)
		app.sites.add(get_current_site())
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@testagent.example.org",
			website="http://testagent.example.org"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent=self.upload_agent)

	def test_complete_login_and_callback(self):
		resp = self.client.get(reverse("battlenet_login"), dict(process="login"))
		p = urlparse(resp["location"])
		q = parse_qs(p.query)

		response_json = """{"uid":"battlenet", "access_token":"testac", "refresh_token": "testrf" }"""
		battlenet_response = MockedResponse(200, """{"id": "123456", "battletag": "Nicodemus#1538"}""")
		callback_url = reverse("battlenet_callback")

		with mocked_response(MockedResponse(200, response_json, {"content-type": "application/json"}), battlenet_response):
			response = self.client.get(callback_url, {"code": "35mr8zc6rvx2wek2z4pz2yaj", "state": q["state"][0]})
			self.assertEqual(response.status_code, 302)
			self.assertEqual(urlparse(response["location"]).path, reverse("joust_replay_list"))

	def test_complete_login_with_token_attachment(self):
		attachment_url = reverse("attach_site_upload_token", kwargs={
			"single_site_upload_token": str(self.token.token),
			"api_key": str(self.upload_agent.api_key),
		})
		# Initiate attachment sequence
		response = self.client.get(attachment_url)
		# Confirm that info was stashed in session before sending redirect.
		self.assertTrue("token_attachment_requested" in self.client.session)
		login_url = reverse("battlenet_login")
		# Confirm that the redirect is the same as the battlenet_login url
		self.assertEqual(login_url, urlparse(response["location"]).path)

		# Invoke the login url because we need the state query param to be generated.
		resp = self.client.get(login_url, dict(process="login"))
		p = urlparse(resp["location"])
		q = parse_qs(p.query)

		response_json = """{"uid":"battlenet", "access_token":"testac", "refresh_token": "testrf" }"""
		battlenet_response = MockedResponse(200, """{"id": "123456", "battletag": "Nicodemus#1538"}""")
		callback_url = reverse("battlenet_callback")

		# Now invoke the callback url with mocked responses to confirm that the token attachment process gets completed.
		with mocked_response(MockedResponse(200, response_json, {"content-type": "application/json"}), battlenet_response):
			response = self.client.get(callback_url, {"code": "35mr8zc6rvx2wek2z4pz2yaj", "state": q["state"][0]})
			self.assertEqual(response.status_code, 302)
			self.assertEqual(urlparse(response["location"]).path, reverse("joust_replay_list"))

		self.assertEqual(User.objects.filter(username="Nicodemus#1538").count(), 1)
		self.assertEqual(SingleSiteUploadToken.objects.get(token=self.token.token).user.username, "Nicodemus#1538")
