from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse


class TestAttachUploadTokenToUser(TestCase):

	def setUp(self):
		super().setUp()
		self.user = User.objects.create_user("andrew", email="andrew@test.com", password="password")

	def test_private_collection(self):
		self.client.login(username = "andrew", password="password")
		response = self.client.get(reverse('private_replay_collection'))
		self.assertEqual(response.templates[0].name, 'joust/private_replay_collection.html')
