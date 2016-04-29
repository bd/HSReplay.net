from django.db import models
from django.core.urlresolvers import reverse
import uuid
from datetime import date
from django.utils import timezone
from django.conf import settings
import boto3
from zlib import decompress, compress
import logging
from django.conf import settings


logger = logging.getLogger(__name__)

_s3_client = boto3.client('s3')


# This function to make it easier to mock out S3 in unit tests.
def get_s3_client():
	return _s3_client


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


class SingleGameRawLogUpload(models.Model):
	"""Represents an upload of raw Hearthstone log data

	The metadata captured is what was provided by the uploader. The raw logs have not yet been parsed for validity.
	"""
	id = models.UUIDField(primary_key=True, editable=False)
	upload_token = models.ForeignKey(SingleSiteUploadToken)
	upload_timestamp = models.DateTimeField()
	match_start_timestamp = models.DateTimeField() # Required, but we use upload_timestamp as a fallback if missing.

	# Can we make these fields readonly outside of this instance? Nobody outside of the save() method should set these directly
	storage_bucket = models.CharField(max_length=65)
	storage_key = models.CharField(max_length=100)

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

	@property
	def log(self):

		if not hasattr(self, "_log"):
			# This is either:
			# 1) a new instance that hasn't been saved() yet
			# 2) an instance returned from the DB and this is the first attribute access

			if not len(self.storage_bucket) or not len(self.storage_key):

				if not self.id:
					# This is a new instance and the log setter method hasn't been used yet, so logically this attribute has no data
					return None
				else:
					# This condition means the data has been corrupted.
					# If it has a DB ID, then it's an old instance which should never have been able to be saved without the pointers to the underlying data set.
					# It's also possible that they were set when it was saved but have been subsequently been deleted.
					msg = "Corrupt Data! %s with id %s. Object has a DB ID but not a pointer to any actual log data." % (self.__class__.__name__, str(self.id))
					logger.error(msg)
					raise Exception(msg)

			try:
				s3_obj = get_s3_client().get_object(Bucket=self.storage_bucket, Key=self.storage_key)
				if 'ContentEncoding' in s3_obj and s3_obj['ContentEncoding'] == 'gzip':
					self._log = decompress(s3_obj['Body'].read())
				else:
					self._log = s3_obj['Body'].read()

			except Exception as e:
				logger.error("Failure retreiving data from S3 for raw upload with id %s" % str(self.id))
				logger.exception(e)
				raise e

		return self._log

	@log.setter
	def log(self, data):
		self._log = data
		self._log_data_set = True

	def _references_data_in_s3(self):
		return len(self.storage_bucket) and len(self.storage_key)

	def save(self, *args, **kwargs):
		if not self._references_data_in_s3() and not hasattr(self, "_log"):
			raise ValueError("The log attribute is required. You must set it on new objects before attempting to save.")

		if getattr(self, "_log_data_set", False):
			# We must write the log data to S3 here.

			if not self.match_start_timestamp:
				raise ValueError("match_start_timestamp is required.")

			self.id = uuid.uuid4()
			self.storage_bucket = settings.S3_RAW_LOG_STORAGE_BUCKET
			self.storage_key = self.match_start_timestamp.strftime('%Y/%m/%d/') + str(self.id)

			try:
				get_s3_client().put_object(Body=compress(self._log), Bucket=self.storage_bucket, Key=self.storage_key, ContentEncoding='gzip')
			except Exception as e:
				logger.exception(e)

		else:
			# The log data was saved previously, and wasn't mutated so no resaving is required.
			pass

		return super(SingleGameRawLogUpload, self).save(*args, **kwargs)

	def delete(self, using=None, stop_on_s3_error=False):

		if self._references_data_in_s3():
			# We must delete the key in S3 so that we don't leave it orphaned in the bucket.
			try:
				get_s3_client().delete_object(Bucket=self.storage_bucket, Key=self.storage_key)
			except Exception as e:
				logger.exception(e)
				# By default we don't block the delete if the record is missing.
				# Orphaning the object is not the end of the world
				if stop_on_s3_error:
					raise e

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
