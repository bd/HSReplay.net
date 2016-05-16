from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase


class TestAttachUploadTokenToUser(TestCase):
	def setUp(self):
		super().setUp()
		self.user = User.objects.create_user("andrew", email="andrew@test.com", password="password")

	def test_private_collection(self):
		self.client.login(username="andrew", password="password")
		response = self.client.get(reverse("my_replays"))
		self.assertEqual(response.templates[0].name, "joust/my_replays.html")
