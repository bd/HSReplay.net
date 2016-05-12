import uuid
import logging
import re
from datetime import date, datetime, timedelta
from io import StringIO
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from hearthstone.enums import *
from hsreplay import __version__ as hsreplay_version
from hsreplay.dumper import parse_log, create_document, game_to_xml
from hsreplay.utils import pretty_xml
from cards.models import Card, Deck


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
	return '%sreplays/%s.xml' % (instance.global_game.match_start_timestamp.strftime('%Y/%m/%d/'), str(instance.id))


def _validate_valid_game_type(value):
	if value:
		try:
			BnetGameType(value)
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

def _validate_friendly_player_id(value):
	if value:
		if value != 1 and value != 2:
			raise ValidationError("friendly_player_id must be either 1 or 2. %s is not valid." % value)


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

	game_type = models.IntegerField(null=True, blank=True, validators=[_validate_valid_game_type])
	is_spectated_game = models.BooleanField(default=False)
	friendly_player_id = models.IntegerField(null=True, blank=True, validators=[_validate_friendly_player_id])
	scenario_id = models.IntegerField(null=True, blank=True)

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

	def _generate_game_meta_data(self):
		meta_data = {}

		if self.game_type:
			meta_data["type"] = str(self.game_type)

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


class GlobalGame(models.Model):
	"""Represents a globally unique game (e.g. from the perspective of the server).

	The fields on this object represent information that is public to all players and spectators. When the same game is
	uploaded by multiple players or spectators they will all share a reference to a single global game.

	When a replay or raw log file is uploaded the server first checks for the existence of a GlobalGame record. It looks
	for any games that occured on the same region where both players have matching battle_net_ids and where the match
	start timestamp is within +/- 1 minute from the timestamp on the upload. The +/- range on the match start timestamp
	is to account for potential clock drift between the computer that generated this replay and the computer that uploaded
	the earlier record which first created the GlobalGame record. If no existing GlobalGame record is found, then one is
	created.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

	# Note: The Innkeeper does not share the same accountHi value as real Battle.net Accounts
	bnet_region_id = models.CharField(max_length=50,
								   verbose_name="Battle.net Region ID",
								   help_text="This is the accountHi value from either Player entity.")

	# We believe game_id is not monotonically increasing as it appears to roll over and reset periodically.
	game_server_game_id = models.IntegerField(null=True,
								  verbose_name="Battle.net Game ID",
								  help_text="This is the game_id from the Net.log")
	game_server_address = models.GenericIPAddressField(null=True, blank=True)
	game_server_port = models.IntegerField(null=True, blank=True)

	hearthstone_build = models.CharField(max_length=50,
										 null=True,
										 verbose_name="Hearthstone Build Number",
										 help_text="This can be discovered by inspecting the game client executable.")

	match_start_timestamp = models.DateTimeField(verbose_name="Match Start Timestamp",
												 help_text="This must be a timezone aware datetime.")

	match_end_timestamp = models.DateTimeField(verbose_name="Match End Timestamp",
												 help_text="This must be a timezone aware datetime.")

	# The BnetGameType enum encodes whether it's ranked or casual as well as standard or wild.
	game_type = models.IntegerField(null=True,
									verbose_name="Game Type",
									help_text="A value from hearthstone.enums.BnetGameType")

	# ladder_season is nullable since not all games are ladder games, e.g. Adventure or Arena.
	ladder_season = models.IntegerField(null=True,
										verbose_name="Ladder Season",
										help_text="The season as calculated from the match start timestamp.")

	# Nullable, since not all replays are TBs. Will currently have no way to calculate this so it will always be null for now.
	brawl_season = models.IntegerField(null=True,
									   verbose_name="Brawl Season",
									   help_text="The brawl season which resets each week when the brawl changes.")

	# Nullable, We currently have no way to discover this.
	scenario_id = models.IntegerField(null=True,
									  verbose_name="Scenario ID",
									  help_text="Indicates which Adventure or Brawl logic the server should use.")

	# For Adventure bosses & The Innkeeper this value is "0"
	player_one_battlenet_id = models.CharField(max_length=50,
											   verbose_name="Player 1 Battle.net ID",
											   help_text="The accountLo value from the Player entity.")

	# The player can change their hero during a game, e.g. via Jaraxxas or Major Domo.
	# In tavern brawl its possible for this to be a hero like Nefarian or Ragnaros.
	player_one_starting_hero_id = models.CharField(max_length=50,
												   verbose_name="Player 1 Starting Hero Card ID",
												   help_text="The CardID representing Player 1's initial hero.")

	# In tavern brawls if the hero is a card like Nefarian or Ragnaros this value will be "0" or CardClass.NEUTRAL
	player_one_starting_hero_class = models.IntegerField(verbose_name="Player 1 Starting Hero Class",
														 help_text="A value from hearthstone.enums.CardClass.")

	# It is possible for both players to loose a match (but not both for both players to loose).
	player_one_final_state = models.IntegerField(verbose_name="Player 1 Final State",
												help_text="A value from hearthstone.enums.PlayState.")

	### The next 3 fields all identical to the previous 3, but for Player 2 ###
	player_two_battlenet_id = models.CharField(max_length=50,
											   verbose_name="Player 2 Battle.net ID",
											   help_text="The accountLo value from the Player entity.")

	player_two_starting_hero_id = models.CharField(max_length=50,
												   verbose_name="Player 1 Starting Hero Card ID",
												   help_text="The CardID representing Player 1's initial hero.")

	player_two_starting_hero_class = models.IntegerField(verbose_name="Player 1 Starting Hero Class",
														 help_text="A value from hearthstone.enums.CardClass.")

	player_two_final_state = models.IntegerField(verbose_name="Player 2 Final State",
												 help_text="A value from hearthstone.enums.PlayState.")

	# The following basic stats are globally visible to all
	num_turns = models.IntegerField()
	num_entities = models.IntegerField()


class GameReplayUploadManager(models.Manager):

	def create_from_raw_log_upload(self, raw_log):
		# Don't attempt to create a replay if validation doesn't pass
		raw_log.full_clean()

		raw_log.log.open()  # Make sure that the file is open to the beginning of it.
		raw_log_str = raw_log.log.read().decode("utf-8")
		packet_tree = parse_log(StringIO(raw_log_str), processor='GameState', date=raw_log.match_start_timestamp)

		if not len(packet_tree.games):
			# We were not able to generate a replay
			raise ValidationError("Could not parse a replay from the raw log data")

		replay_tree = create_document(version=hsreplay_version, build=raw_log.hearthstone_build)

		game = game_to_xml(packet_tree.games[0],
						   game_meta=raw_log._generate_game_meta_data(),
						   player_meta=raw_log._generate_player_meta_data(),
						   decks=raw_log._generate_deck_lists())

		replay_tree.append(game)

		bnet_region_id = None
		player_one_battlenet_id = None
		player_two_battlenet_id = None

		for player in replay_tree.iter("Player"):
			if player.get('playerID') == '1':
				player_one_battlenet_id = player.get('accountLo')

			if player.get('playerID') == '2':
				player_two_battlenet_id = player.get('accountLo')

			# The Innkeeper and Adventure bosses might have a different accountHi value so we must find a human player.
			if player.get('accountLo') != '0':
				bnet_region_id = player.get('accountHi')

		if not bnet_region_id:
			raise ValidationError("Could not locate a battle.net region ID which is required.")

		if not player_one_battlenet_id:
			raise ValidationError("Could not locate Player 1's Battle.net ID which is required.")

		if not player_two_battlenet_id:
			raise ValidationError("Could not locate Player 2's Battle.net ID which is required.")


		global_game = GlobalGame.objects.filter(bnet_region_id=bnet_region_id,
												  game_server_address=raw_log.game_server_address,
												  game_server_port=raw_log.game_server_port,
												  game_server_game_id=raw_log.game_server_game_id,
												  player_one_battlenet_id=player_one_battlenet_id,
												  player_two_battlenet_id=player_two_battlenet_id).first()

		if global_game:
			# If a global_game already exists then there is a possibility that this is a duplicate upload, so check for it.
			duplicate = GameReplayUpload.objects.filter(upload_token=raw_log.upload_token, global_game=global_game).first()
			if duplicate:
				raise ValidationError("This replay has already been uploaded by this user and has UUID: %s" % str(duplicate.id))
		else:
			global_game = GlobalGame.objects.create(bnet_region_id=bnet_region_id,
									 brawl_season=None,
									 game_server_game_id=raw_log.game_server_game_id,
									 game_server_address = raw_log.game_server_address,
									 game_server_port = raw_log.game_server_port,
									 game_type=raw_log.game_type,
									 hearthstone_build=raw_log.hearthstone_build,
									 ladder_season=self._current_season_number(raw_log.match_start_timestamp),
									 match_end_timestamp=self._find_match_end_timestamp(packet_tree),
									 match_start_timestamp=raw_log.match_start_timestamp,
									 num_entities=self._get_num_entities(packet_tree),
									 num_turns=self._get_num_turns(packet_tree),
									 player_one_battlenet_id=player_one_battlenet_id,
									 player_one_starting_hero_class=self._get_starting_hero_class_for_player(0, packet_tree),
									 player_one_starting_hero_id=self._get_starting_hero_for_player(0,packet_tree).card_id,
									 player_one_final_state = self._get_final_state_for_player(0, packet_tree),
									 player_two_battlenet_id=player_two_battlenet_id,
									 player_two_starting_hero_class=self._get_starting_hero_class_for_player(1, packet_tree),
									 player_two_starting_hero_id=self._get_starting_hero_for_player(1,packet_tree).card_id,
									 player_two_final_state=self._get_final_state_for_player(1, packet_tree),
									 scenario_id=raw_log.scenario_id)

		replay_upload = GameReplayUpload(
			friendly_player_id = raw_log.friendly_player_id,
			game_server_client_id = raw_log.game_server_client_id,
			game_server_spectate_key = raw_log.game_server_spectate_key,
			global_game = global_game,
			hsreplay_version = hsreplay_version,
			is_spectated_game = raw_log.is_spectated_game,
			player_one_name = self._get_name_for_player(0, packet_tree),
			player_one_starting_deck_list = self._get_starting_deck_list_for_player(0, packet_tree, raw_log),
			player_two_name = self._get_name_for_player(1, packet_tree),
			player_two_starting_deck_list = self._get_starting_deck_list_for_player(1, packet_tree, raw_log),
			raw_log = raw_log,
			upload_timestamp = raw_log.upload_timestamp,
			upload_token = raw_log.upload_token)

		replay_upload.replay_xml.save('hsreplay.xml', ContentFile(pretty_xml(replay_tree)), save=False)
		replay_upload.save()

		return replay_upload

	def _get_starting_deck_list_for_player(self, num, packet_tree, raw_log):
		#If the raw_log has a deck_list then the client has uploaded a complete 30 card list which takes precedence.
		starting_deck_card_ids = None
		if num == 0:
			if raw_log.player_1_deck_list:
				starting_deck_card_ids = raw_log.player_1_deck_list.split(',')
			else:
				starting_deck_card_ids = [e.card_id for e in packet_tree.games[0].players[num].initial_deck if e.card_id]
			return Deck.objects.get_or_create_from_id_list(starting_deck_card_ids)

		if num == 1:
			if raw_log.player_2_deck_list:
				starting_deck_card_ids = raw_log.player_2_deck_list.split(',')
			else:
				starting_deck_card_ids = [e.card_id for e in packet_tree.games[0].players[num].initial_deck if e.card_id]
			return Deck.objects.get_or_create_from_id_list(starting_deck_card_ids)

	def _get_name_for_player(self, num, packet_tree):
		return packet_tree.games[0].players[num].name

	def _get_final_state_for_player(self, num, packet_tree):
		return packet_tree.games[0].players[num].tags.get(GameTag.PLAYSTATE)

	def _get_starting_hero_class_for_player(self, num, packet_tree):
		hero_card_id = self._get_starting_hero_for_player(num, packet_tree).card_id
		card = Card.objects.get(id=hero_card_id)
		return CardClass(card.card_class)

	def _get_starting_hero_for_player(self, num, packet_tree):
		return list(packet_tree.games[0].players[num].heroes)[0]

	def _get_num_turns(self, packet_tree):
		return packet_tree.games[0].tags.get(GameTag.TURN)

	def _get_num_entities(self, packet_tree):
		return max(e.id for e in packet_tree.games[0].entities)

	def _find_match_end_timestamp(self, packet_tree):
		if len(packet_tree.games) > 1:
			raise Exception("This method of determining match end timestamp is only valid for single game replays.")

		return packet_tree._current_date

	def _current_season_number(self, match_start_timestamp):
		# Using Jan'2016 as a psuedo-epoch start since we know that is season 22
		epoch_start = datetime(2016, 1, 1)
		epoch_start_season = 22

		delta_months = (match_start_timestamp.year - epoch_start.year) * 12 + (match_start_timestamp.month - epoch_start.month)
		return epoch_start_season + delta_months


class GameReplayUpload(models.Model):
	""" Represents a replay as captured from the point of view of a single packet stream sent to a Hearthstone client.

	Replays can be uploaded by either of the players or by any number of spectators who watched the match. It is possible
	that the same game could be uploaded from multiple points of view. When this happens each GameReplayUpload will point
	to the same GlobalGame record via the global_game foreign key.

	It is possible that different uploads of the same game will have different information in them. For example:
		- If Player A and Player B are Real ID Friends and Player C is Battle.net friends with just Player B, then when
		Player C spectates a match between Players A and B, his uploaded replay will show the BattleTag as the name of
		Player A. However if Player B uploads a replay of the same match, his replay will show the real name for Player A.

		- Likewise, if Player C either starts spectating the game after it has already begun or stops spectating before
		 it ends, then his uploaded replay will have fewer turns of gameplay then Player B's replay.

	"""
	class Meta:
		unique_together = ("upload_token", "global_game")

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	objects = GameReplayUploadManager()
	upload_token = models.ForeignKey(SingleSiteUploadToken,
									 related_name="replays",
									 help_text="The upload token used by the owner of the replay when uploading it.")
	upload_timestamp = models.DateTimeField()
	global_game = models.ForeignKey(GlobalGame,
									related_name="replays",
									help_text="References the single global game that this replay shows.")

	# raw_log can be null because a user might upload the XML of a replay directly.
	raw_log = models.ForeignKey(SingleGameRawLogUpload, related_name="replays", null=True)

	# This is useful to know because replays that are spectating both players will have more data then those from a single player.
	# For example, they will have access to the cards that are in each players hand.
	# This is detectable from the raw logs, although we currently intend to have the client uploading the replay provide it.
	is_spectated_game = models.BooleanField(default=False)

	# The "friendly player" is the player whose cards are at the bottom of the screen when watching a game.
	# For spectators this is determined by which player they started spectating first (if they spectate both).
	friendly_player_id = models.IntegerField(null=True,
											help_text="Either 1 or 2, to indicate which Player entity is the friendly entity.")

	player_one_name = models.CharField(max_length=255,
										verbose_name="Player 1 Name",
										help_text="Either the first part of a BattleTag or a name for Real ID Friends.")

	player_two_name = models.CharField(max_length=255,
										verbose_name="Player 2 Name",
										help_text="Either the first part of a BattleTag or a name for Real ID Friends.")


	# This information is all optional and is from the Net.log ConnectAPI
	game_server_spectate_key = models.CharField(max_length=50, null=True, blank=True)
	game_server_client_id = models.IntegerField(null=True, blank=True)

	replay_xml = models.FileField(upload_to=_generate_replay_upload_key)
	hsreplay_version = models.CharField(max_length=20,
										help_text="The value of hsreplay.__version__ when the replay was generated.")

	player_one_starting_deck_list = models.ForeignKey(Deck,
									 					related_name="+",
									 					help_text="The set of cards revealed from the player's initial deck list")

	# FK to deck_list as extracted from the replay XML, which might not include all 30 cards.
	player_two_starting_deck_list = models.ForeignKey(Deck,
														 related_name="+",
														 help_text="The set of cards revealed from the player's initial deck list")

	# The fields below capture the preferences of the user who uploaded it.
	is_deleted = models.BooleanField(default=False) # User indicated in UI to delete replay upload (don't include in query sets)
	exclude_in_aggregate_stats = models.BooleanField(default=False)
	is_public = models.BooleanField(default=False)


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
