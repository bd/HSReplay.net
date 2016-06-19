from enum import IntEnum
from django.core.urlresolvers import reverse
from django.utils.timezone import now
from django.db import models
from django.core.files.storage import default_storage
from hsreplaynet.utils.fields import IntEnumField, ShortUUIDField


class UploadEventType(IntEnum):
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


class UploadEventStatus(IntEnum):
	UNKNOWN = 0
	PROCESSING = 1
	SERVER_ERROR = 2
	PARSING_ERROR = 3
	SUCCESS = 4


def _generate_upload_path(instance, filename):
	ts = now()
	extension = UploadEventType(instance.type).extension
	if instance.token:
		token = str(instance.token.key)
	else:
		token = "unknown-token"
	yymmdd = ts.strftime("%Y/%m/%d")
	return "uploads/%s/%s/%s%s" % (yymmdd, token, ts.isoformat(), extension)


class UploadEventManager(models.Manager):
	def get_by_bucket_and_key(self, bucket, key):
		if key.endswith(UploadEventType.POWER_LOG.extension):
			db_id = key[19:-10]
			return self.objects.get(id=db_id)


class UploadEvent(models.Model):
	"""
	Represents a game upload, before the creation of the game itself.

	The metadata captured is what was provided by the uploader.
	The raw logs have not yet been parsed for validity.
	"""
	id = models.BigAutoField(primary_key=True)
	shortid = ShortUUIDField("Short ID")
	token = models.ForeignKey("api.AuthToken", null=True, blank=True, related_name="uploads")
	type = IntEnumField(enum=UploadEventType)
	game = models.ForeignKey("games.GameReplay", null=True, blank=True, related_name="uploads")
	created = models.DateTimeField(auto_now_add=True)
	upload_ip = models.GenericIPAddressField()
	status = IntEnumField(enum=UploadEventStatus, default=UploadEventStatus.UNKNOWN)
	tainted = models.BooleanField(default=False)

	metadata = models.TextField()
	file = models.FileField(upload_to=_generate_upload_path)

	objects = UploadEventManager()

	def delete(self, using=None):
		# We must cleanup the S3 object ourselves (It is not handled by django-storages)
		if default_storage.exists(self.file.name):
			self.file.delete()

		return super(UploadEvent, self).delete(using)

	def get_absolute_url(self):
		return reverse("upload_detail", kwargs={"shortid": self.shortid})

	def process(self):
		from hsreplaynet.games.processing import process_upload_event

		process_upload_event(self)
