from django.test import TestCase
from web.models import *
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialLogin
from allauth.socialaccount.helpers import complete_social_login
from allauth.account import app_settings as account_settings
from django.test.utils import override_settings


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

	@override_settings(
        SOCIALACCOUNT_AUTO_SIGNUP=True,
        ACCOUNT_SIGNUP_FORM_CLASS=None,
        ACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.NONE  # noqa
    )
	def test_token_attached_after_social_login(self):
		factory = RequestFactory()
		request = factory.get('/accounts/login/callback/')
		request.user = AnonymousUser()
		SessionMiddleware().process_request(request)
		MessageMiddleware().process_request(request)

		account = SocialAccount(provider='battlenet', uid='123')
		sociallogin = SocialLogin(user=self.user, account=account)
		complete_social_login(request, sociallogin)
