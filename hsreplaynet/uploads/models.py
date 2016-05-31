import uuid
from enum import IntEnum
from django.core.urlresolvers import reverse
from django.db import models
from hsreplaynet.fields import IntEnumField


class GameUploadType(IntEnum):
	POWER_LOG = 1
	OUTPUT_TXT = 2
	HSREPLAY_XML = 3

	@property
	def extension(self):
		if self.name == "POWER_LOG":
			return ".power.log"
		elif self.name == "OUTPUT_TXT":
			return ".output.txt"
		elif self.name == "HSREPLAY_XML":
			return ".hsreplay.xml"
		return ".txt"


class GameUploadStatus(IntEnum):
	UNKNOWN = 0
	PROCESSING = 1
	SERVER_ERROR = 2
	PARSING_ERROR = 3
	SUCCESS = 4


def _generate_key(instance, filename):
	timestamp = instance.created.strftime("%Y/%m/%d")
	extension = GameUploadType(instance.type).extension
	return "uploads/%s/%s%s" % (timestamp, str(instance.id), extension)


class GameUploadManager(models.Manager):
	def get_by_bucket_and_key(self, bucket, key):
		if key.endswith(GameUploadType.POWER_LOG.extension):
			db_id = key[19:-10]
			return self.objects.get(id=db_id)


class GameUpload(models.Model):
	"""
	Represents a game upload, before the creation of the game itself.

	The metadata captured is what was provided by the uploader.
	The raw logs have not yet been parsed for validity.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	token = models.ForeignKey("api.AuthToken", null=True, blank=True)
	type = IntEnumField(enum=GameUploadType)
	game = models.ForeignKey("web.GameReplayUpload", null=True, blank=True)
	created = models.DateTimeField(auto_now_add=True)
	upload_ip = models.GenericIPAddressField()
	status = IntEnumField(enum=GameUploadStatus)
	tainted = models.BooleanField(default=False)

	metadata = models.TextField()
	file = models.FileField(upload_to=_generate_key)

	objects = GameUploadManager()

	def get_absolute_url(self):
		return reverse("upload_detail", kwargs={"id": str(self.id)})


class UploadEventProcessingRequest(models.Model):
	"""
	Represents a message published to an SNS Topic to schedule
	an UploadEvent for Processing.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	created = models.DateTimeField(auto_now_add=True)
	upload_event = models.ForeignKey(GameUpload)
	sns_topic_arn = models.CharField(max_length=100)
	sns_message_id = models.CharField(max_length=100)
