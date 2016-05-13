from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from web.models import *


class TestAttachUploadTokenToUser(TestCase):
	def setUp(self):
		super().setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@testagent.example.org",
			website="http://testagent.example.org"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent=self.upload_agent)
		self.user = User.objects.create_user("andrew", email="andrew@example.com", password="password")
		self.attachment_url = reverse("attach_site_upload_token", kwargs={
			"single_site_upload_token": str(self.token.token),
			"api_key": str(self.upload_agent.api_key),
		})

	def test_user_already_logged_in(self):
		self.client.login(username="andrew", password="password")
		response = self.client.get(self.attachment_url)
		self.assertEqual(response.context["token"], str(self.token.token))
		self.assertEqual(response.templates[0].name, "web/token_attached.html")
		self.assertEqual(SingleSiteUploadToken.objects.get(token=self.token.token).user, self.user)

	def test_not_logged_in_triggers_redirect(self):
		response = self.client.get(self.attachment_url)
		self.assertEqual(response.status_code, 302)
