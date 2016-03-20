from django.test import TestCase
from web.models import *
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User


class TestAttachUploadTokenToUser(TestCase):

	def setUp(self):
		super().setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)
		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent = self.upload_agent)
		self.user = User.objects.create_user("andrew", email="andrew@test.com", password="password")

	def test_user_already_logged_in(self):
		self.client.login(username="andrew", password="password")
		attachment_url = reverse('attach_site_upload_token', kwargs={'api_key':str(self.upload_agent.api_key),
																	 'single_site_upload_token': str(self.token.token)})
		response = self.client.get(attachment_url)
		self.assertEqual(response.context['token'], str(self.token.token))
		self.assertEqual(response.templates[0].name, 'web/token_attached.html')
		self.assertEqual(SingleSiteUploadToken.objects.get(token=self.token.token).user, self.user)

	def test_not_logged_in_triggers_redirect(self):
		attachment_url = reverse('attach_site_upload_token', kwargs={'api_key':str(self.upload_agent.api_key),
																	 'single_site_upload_token': str(self.token.token)})
		response = self.client.get(attachment_url)
		self.assertEqual(response.status_code, 302)
