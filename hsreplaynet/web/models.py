from django.db import models
from django.core.urlresolvers import reverse
import uuid
from datetime import date
from django.utils import timezone
import logging
from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


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


def _generate_raw_log_key(instance, filename):
	return '%s%s/Power.log' % (instance.match_start_timestamp.strftime('%Y/%m/%d/'), str(instance.id))


class SingleGameRawLogUpload(models.Model):
	"""Represents an upload of raw Hearthstone log data.

	The metadata captured is what was provided by the uploader. The raw logs have not yet been parsed for validity.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	upload_token = models.ForeignKey(SingleSiteUploadToken)
	upload_timestamp = models.DateTimeField()
	match_start_timestamp = models.DateTimeField() # Required, but we use upload_timestamp as a fallback if missing.

	# This will get transparently gzipped and stored in S3
	log = models.FileField(upload_to=_generate_raw_log_key)

	# All the remaining fields represent optional meta data the client can provide when uploading a replay.
	hearthstone_build = models.CharField(max_length=50, null=True)
	match_type = models.IntegerField(null=True)
	is_ranked = models.NullBooleanField(null=True)

	# Player Info
	player_1_rank = models.IntegerField(null=True)
	player_1_legend_rank = models.IntegerField(null=True)
	player_1_deck_list = models.CharField(max_length=255, null=True)
	player_2_rank = models.IntegerField(null=True)
	player_2_legend_rank = models.IntegerField(null=True)
	player_2_deck_list = models.CharField(max_length=255, null=True)

	# Connection Info
	game_server_reconnecting = models.NullBooleanField(null=True)
	game_server_address = models.GenericIPAddressField(null=True)
	game_server_port = models.IntegerField(null=True)
	game_server_game_id = models.IntegerField(null=True)
	game_server_client_id = models.IntegerField(null=True)
	game_server_spectate_key = models.CharField(max_length=50, null=True)

	def delete(self, using=None):
		# We must cleanup the S3 object ourselves (It is not handled by django-storages)
		if default_storage.exists(self.log.name):
			self.log.delete()

		return super(SingleGameRawLogUpload, self).delete(using)


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
