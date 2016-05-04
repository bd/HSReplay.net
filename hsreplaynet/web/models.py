from django.db import models
from django.core.urlresolvers import reverse
import uuid
from datetime import date
from django.utils import timezone
import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from hsreplay.dumper import parse_log, create_document, game_to_xml, __version__ as hsreplay_version
from hsreplay.utils import pretty_xml
from hearthstone.enums import GameType
from io import StringIO
from cards.models import Card

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


def _generate_replay_upload_key(instance, filename):
	uuid = None #Either the ID of the raw log record or
	return '%s%s/hsreplay.xml' % (instance.match_start_timestamp.strftime('%Y/%m/%d/'), str(instance.id))


def _validate_valid_match_type(value):
	if value:
		try:
			GameType(value)
		except ValueError as e:
			raise ValidationError(e)

def _validate_player_rank(value):
	if value:
		if value > 26 or value < 1:
			raise ValidationError("%s is not a valid player rank between 26 and 1." % value)

def _validate_player_legend_rank(value):
	if value:
		if value < 1:
			raise ValidationError("%s is not a valid legend rank." % value)

def _validate_player_deck_list(value):
	if value:
		cards = value.split(',')

		if len(cards) != 30:
			raise ValidationError("player_deck_lists must contain 30 comma separated card IDs.")

		for cardId in cards:
			if not cardId in Card.objects.get_valid_deck_list_card_set():
				raise ValidationError("%s is not a valid cardID")


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
	hearthstone_build = models.CharField(max_length=50, null=True, blank=True)
	match_type = models.IntegerField(null=True, blank=True, validators=[_validate_valid_match_type])
	is_ranked = models.NullBooleanField(null=True, blank=True)

	# Player Info
	player_1_rank = models.IntegerField(null=True, blank=True, validators=[_validate_player_rank])
	player_1_legend_rank = models.IntegerField(null=True, blank=True, validators=[_validate_player_legend_rank])
	player_1_deck_list = models.CharField(max_length=255, null=True, blank=True, validators=[_validate_player_deck_list])
	player_2_rank = models.IntegerField(null=True, blank=True, validators=[_validate_player_rank])
	player_2_legend_rank = models.IntegerField(null=True, blank=True, validators=[_validate_player_legend_rank])
	player_2_deck_list = models.CharField(max_length=255, null=True, blank=True, validators=[_validate_player_deck_list])

	# Connection Info
	game_server_reconnecting = models.NullBooleanField(null=True, blank=True)
	game_server_address = models.GenericIPAddressField(null=True, blank=True)
	game_server_port = models.IntegerField(null=True, blank=True)
	game_server_game_id = models.IntegerField(null=True, blank=True)
	game_server_client_id = models.IntegerField(null=True, blank=True)
	game_server_spectate_key = models.CharField(max_length=50, null=True, blank=True)

	def delete(self, using=None):
		# We must cleanup the S3 object ourselves (It is not handled by django-storages)
		if default_storage.exists(self.log.name):
			self.log.delete()

		return super(SingleGameRawLogUpload, self).delete(using)

	def clean(self):
		if self.player_1_rank and self.player_1_legend_rank:
			raise ValidationError("Player 1 has both rank and legend_rank set. Only one or the other is valid.")

		if self.player_2_rank and self.player_2_legend_rank:
			raise ValidationError("Player 2 has both rank and legend_rank set. Only one or the other is valid.")

		return super(SingleGameRawLogUpload, self).clean()

	def generate_replay(self):

		parser = parse_log(StringIO(self.log.read()), processor='GameState', date=self.match_start_timestamp)
		doc = create_document(version=hsreplay_version, build=self.hearthstone_build)
		game = game_to_xml(parser.games[0],
						   game_meta=self._generate_game_meta_data(),
						   player_meta=self._generate_game_meta_data(),
						   decks=self._generate_deck_lists())
		doc.append(game)

		replay_xml = pretty_xml(doc)
		return replay_xml

	def _generate_game_meta_data(self):
		return {"type":"7",
				"id":"16777509",
				"x-address":"80.239.211.201:3724",
				"x-clientid":"652227",
				"x-spectateKey":"NoLImk",
				"reconnecting":"False"}

	def _generate_player_meta_data(self):
		return [{}, {}]

	def _generate_deck_lists(self):
		return [[], []]


# class SingleGameReplayUpload(models.Model):
# 	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# 	# This will get transparently gzipped and stored in S3
# 	replay = models.FileField(upload_to=_generate_raw_log_key)
# 	raw_log = models.ForeignKey(SingleGameRawLogUpload, null=True)
# 	md5_hexdigest = models.CharField(max_length=32)


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
