import uuid
from django.db import models
from hsreplaynet.web.models import SingleSiteUploadToken


class UploadAgentAPIKey(models.Model):
	full_name = models.CharField(max_length=254)
	email = models.EmailField()
	website = models.URLField(blank=True)
	api_key = models.UUIDField(blank=True)

	tokens = models.ManyToManyField(SingleSiteUploadToken)

	def __str__(self):
		return self.full_name

	def save(self, *args, **kwargs):
		self.api_key = uuid.uuid4()
		return super(UploadAgentAPIKey, self).save(*args, **kwargs)
