import uuid
from django.conf import settings
from django.db import models
from hsreplaynet.utils import generate_key


class AuthToken(models.Model):
	key = models.CharField("Key", max_length=40, primary_key=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL,
		related_name="auth_tokens", null=True, blank=True
	)
	created = models.DateTimeField("Created", auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.key:
			self.key = generate_key()
		return super(AuthToken, self).save(*args, **kwargs)

	def __str__(self):
		return self.key


class UploadAgentAPIKey(models.Model):
	full_name = models.CharField(max_length=254)
	email = models.EmailField()
	website = models.URLField(blank=True)
	api_key = models.UUIDField(blank=True)
	enabled = models.BooleanField(default=True)

	tokens = models.ManyToManyField(AuthToken)

	def __str__(self):
		return self.full_name

	def save(self, *args, **kwargs):
		if not self.api_key:
			self.api_key = uuid.uuid4()
		return super(UploadAgentAPIKey, self).save(*args, **kwargs)
