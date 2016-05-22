from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from hsreplaynet.web.models import SingleSiteUploadToken
from hsreplaynet.test.base import create_agent_and_token


class TestAttachUploadTokenToUser(TestCase):
	def setUp(self):
		super().setUp()
		self.agent, self.token = create_agent_and_token()
		self.user = User.objects.create_user(
			"test", email="test@example.com", password="password"
		)
		self.attachment_url = reverse("attach_site_upload_token", kwargs={
			"token": str(self.token.token),
			"api_key": str(self.agent.api_key),
		})

	def test_user_already_logged_in(self):
		self.client.login(username="test", password="password")
		response = self.client.get(self.attachment_url)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["token"], self.token)
		self.assertEqual(response.templates[0].name, "web/token_attached.html")
		self.assertEqual(list(self.user.tokens.all()), [self.token])
		self.assertEqual(list(self.agent.tokens.all()), [self.token])
		updated_token = SingleSiteUploadToken.objects.get(token=self.token.token)
		self.assertEqual(updated_token.token, self.token.token)
		self.assertEqual(updated_token.user, self.user)

	def test_not_logged_in_triggers_redirect(self):
		response = self.client.get(self.attachment_url)
		self.assertEqual(response.status_code, 302)
