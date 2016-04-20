from django.db import models
from django.core.urlresolvers import reverse
import uuid
from datetime import date
from django.utils import timezone
from django.conf import settings


class UploadAgentAPIKey(models.Model):
	full_name = models.CharField(max_length=254)
	email = models.EmailField()
	website = models.URLField(blank=True)
	api_key = models.UUIDField(blank=True)

	def save(self, *args, **kwargs):
		self.api_key = uuid.uuid4()
		return super().save(*args, **kwargs)


class SingleSiteUploadToken(models.Model):
	token = models.UUIDField(default=uuid.uuid4, editable=False)
	requested_by_upload_agent = models.ForeignKey(UploadAgentAPIKey)
	created = models.DateTimeField(default=timezone.now)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name='tokens')
	replays_are_public = models.BooleanField(default=False)

	def __str__(self):
		return str(self.token)


class HSReplaySingleGameFileUpload(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	data = models.BinaryField()
	upload_date = models.DateField(default=date.today)
	match_date = models.DateField(null=True)
	player_1_name = models.CharField(max_length=255, null=True)
	player_2_name = models.CharField(max_length=255, null=True)
	upload_token = models.ForeignKey(SingleSiteUploadToken, null=True)
	is_public = models.BooleanField(default=False)
	md5_hexdigest = models.CharField(max_length=32)

	class Meta:
		unique_together = ("upload_token", "md5_hexdigest")

	def get_absolute_url(self):
		return reverse('joust_replay_view', kwargs={'id':self.id})

	def get_s3_key(self):
		return self.match_date.strftime('%Y/%m/%d/') + str(self.id).replace("-", "")
