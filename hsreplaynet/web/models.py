from django.db import models
from django.core.urlresolvers import reverse
import uuid, logging, re
from datetime import date
from django.utils import timezone
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
	return '%slogs/%s.log' % (instance.match_start_timestamp.strftime('%Y/%m/%d/'), str(instance.id))


def _generate_replay_upload_key(instance, filename):
	return '%sreplays/%s.xml' % (instance.match_start_timestamp.strftime('%Y/%m/%d/'), str(instance.id))


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

CREATE_GAME_RAW_LOG_TOKEN = re.compile(r"GameState.DebugPrintPower.*?CREATE_GAME")
def _validate_raw_log(value):
	value.open()
	log_data = value.read().decode("utf8")
	create_game_tokens = CREATE_GAME_RAW_LOG_TOKEN.findall(log_data)
	if len(create_game_tokens) != 1:
		raise ValidationError("Raw log data must only be for a single game.")


class SingleGameRawLogUpload(models.Model):
	"""Represents an upload of raw Hearthstone log data.

	The metadata captured is what was provided by the uploader. The raw logs have not yet been parsed for validity.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	upload_token = models.ForeignKey(SingleSiteUploadToken)
	upload_timestamp = models.DateTimeField()
	match_start_timestamp = models.DateTimeField() # Required, but we use upload_timestamp as a fallback if missing.

	# This will get transparently gzipped and stored in S3
	# The data must be utf-8 encoded bytes
	log = models.FileField(upload_to=_generate_raw_log_key, validators=[_validate_raw_log])

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
		if self.player_1_legend_rank and (self.player_1_rank != 0):
			raise ValidationError("Player 1 has legend rank set to %s, but rank is %s not 0." % (self.player_1_legend_rank, self.player_1_rank))

		if self.player_2_legend_rank and (self.player_2_rank != 0):
			raise ValidationError("Player 2 has legend rank set to %s, but rank is %s not 0." % (self.player_2_legend_rank, self.player_2_rank))

		return super(SingleGameRawLogUpload, self).clean()

	def _generate_replay_element_tree(self):
		# Don't attempt to generate a replay if validation doesn't pass.
		self.full_clean()

		self.log.open() # Make sure that the file is open to the beginning of it.
		raw_log_str = self.log.read().decode("utf-8")
		parser = parse_log(StringIO(raw_log_str), processor='GameState', date=self.match_start_timestamp)

		if not len(parser.games):
			# We were not able to generate a replay
			raise ValidationError("Could not parse a replay from the raw log data")

		doc = create_document(version=hsreplay_version, build=self.hearthstone_build)
		game = game_to_xml(parser.games[0],
						   game_meta=self._generate_game_meta_data(),
						   player_meta=self._generate_player_meta_data(),
						   decks=self._generate_deck_lists())

		doc.append(game)

		return doc

	def _generate_game_meta_data(self):
		meta_data = {}

		if self.match_type:
			meta_data["type"] = str(self.match_type)

		if self.game_server_game_id:
			meta_data["id"] = str(self.game_server_game_id)

		if self.game_server_client_id:
			meta_data["x-clientid"] = str(self.game_server_client_id)

		if self.game_server_address:
			if self.game_server_port:
				meta_data["x-address"] = "%s:%s" % (self.game_server_address, self.game_server_port)
			else:
				meta_data["x-address"] = str(self.game_server_address)

		if self.game_server_spectate_key:
			meta_data["x-spectateKey"] = str(self.game_server_spectate_key)

		if self.game_server_reconnecting:
			meta_data["reconnecting"] = str(self.game_server_reconnecting)

		return meta_data

	def _generate_player_meta_data(self):
		player_one_meta_data = {}
		if self.player_1_rank:
			player_one_meta_data["rank"] = str(self.player_1_rank)

		if self.player_1_legend_rank:
			player_one_meta_data["legendRank"] = str(self.player_1_legend_rank)

		player_two_meta_data = {}
		if self.player_2_rank:
			player_two_meta_data["rank"] = str(self.player_2_rank)

		if self.player_2_legend_rank:
			player_two_meta_data["legendRank"] = str(self.player_2_legend_rank)

		return [player_one_meta_data, player_two_meta_data]

	def _generate_deck_lists(self):
		player_one_deck = None
		if self.player_1_deck_list:
			player_one_deck = self.player_1_deck_list.split(",")

		player_two_deck = None
		if self.player_2_deck_list:
			player_two_deck = self.player_2_deck_list.split(",")

		return [player_one_deck, player_two_deck]


# class SingleGameReplayUpload(models.Model):
# 	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# 	# This will get transparently gzipped and stored in S3
# 	replay = models.FileField(upload_to=_generate_raw_log_key)
# 	# raw_log can be null because we might support direct replay uploads without the raw log files.
# 	raw_log = models.ForeignKey(SingleGameRawLogUpload, null=True)
# 	md5_hexdigest = models.CharField(max_length=32)
#
# 	def save(self, *args, **kwargs):
# 		return super(SingleGameReplayUpload, self).save(*args, **kwargs)



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
