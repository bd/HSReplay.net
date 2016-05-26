import uuid
from enum import IntEnum
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


def _generate_key(instance, filename):
	timestamp = instance.created.strftime("%Y/%m/%d")
	extension = GameUploadType(instance.type).extension
	return "uploads/%s/%s%s" % (timestamp, str(instance.id), extension)


class GameUpload(models.Model):
	"""
	Represents a game upload, before the creation of the game itself.

	The metadata captured is what was provided by the uploader.
	The raw logs have not yet been parsed for validity.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	token = models.ForeignKey("api.AuthToken", null=True, blank=True)
	type = IntEnumField(enum=GameUploadType)
	game = models.ForeignKey("web.GameReplayUpload", null=True)
	created = models.DateTimeField(auto_now_add=True)
	upload_ip = models.GenericIPAddressField()
	failed = models.BooleanField(default=False)

	metadata = models.TextField()
	file = models.FileField(upload_to=_generate_key)
