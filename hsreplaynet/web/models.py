import logging
import re
import uuid
from datetime import datetime
from io import StringIO
from math import ceil
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db import models
from hearthstone.enums import *
from hsreplay import __version__ as hsreplay_version
from hsreplay.dumper import parse_log, create_document, game_to_xml
from hsreplay.utils import toxml
from hsreplaynet.cards.models import Card, Deck
from hsreplaynet.fields import IntEnumField, PlayerIDField
from hsreplaynet.utils import _time_elapsed


logger = logging.getLogger(__name__)
time_logger = logging.getLogger("TIMING")


def _generate_raw_log_key(instance, filename):
	return "%slogs/%s.log" % (instance.match_start_timestamp.strftime("%Y/%m/%d/"), str(instance.id))


def _generate_replay_upload_key(instance, filename):
	return "%sreplays/%s.xml" % (instance.global_game.match_start_timestamp.strftime("%Y/%m/%d/"), str(instance.id))


def find_friendly_player(game_tree):
	for packet in game_tree.packets[1:]:
		if packet.__class__.__name__ != "FullEntity":
			break
		tags = dict(packet.tags)
		if tags[GameTag.ZONE] == Zone.HAND and not packet.cardid:
			return tags[GameTag.CONTROLLER] % 2 + 1


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
		cards = value.split(",")

		if len(cards) != 30:
			raise ValidationError("player_deck_lists must contain 30 comma separated card IDs.")

		for cardId in cards:
			if cardId not in Card.objects.get_valid_deck_list_card_set():
				raise ValidationError("%s is not a valid cardID")


def _validate_raw_log(value):
	CREATE_GAME_RAW_LOG_TOKEN = re.compile(r"GameState.DebugPrintPower.*?CREATE_GAME")
	value.open()
	log_data = value.read().decode("utf8")
	create_game_tokens = CREATE_GAME_RAW_LOG_TOKEN.findall(log_data)
	if len(create_game_tokens) != 1:
		raise ValidationError("Raw log data must contain a single GameState CREATE_GAME token.")


def _validate_friendly_player_id(value):
	if value not in (1, 2):
		raise ValidationError("Invalid friendly_player_id: %r" % (value))


class SingleGameRawLogUpload(models.Model):
	"""
	Represents an upload of raw Hearthstone log data.

	The metadata captured is what was provided by the uploader.
	The raw logs have not yet been parsed for validity.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	upload_token = models.ForeignKey("api.AuthToken", null=True, blank=True)
	upload_timestamp = models.DateTimeField()
	match_start_timestamp = models.DateTimeField(
		help_text="Uses upload_timestamp as a fallback."
	)

	# This will get transparently gzipped and stored in S3
	# The data must be utf-8 encoded bytes
	log = models.FileField(upload_to=_generate_raw_log_key, validators=[_validate_raw_log])

	# All the remaining fields represent optional meta data the client can provide when uploading a replay.
	hearthstone_build = models.CharField(max_length=50, null=True, blank=True)

	game_type = IntEnumField(enum=BnetGameType, null=True, blank=True)
	is_spectated_game = models.BooleanField(default=False)
	friendly_player_id = PlayerIDField(null=True, blank=True)
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

	def get_absolute_url(self):
		return self.log.url

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
	"""
	Represents a globally unique game (e.g. from the server's POV).

	The fields on this object represent information that is public
	to all players and spectators. When the same game is uploaded
	by multiple players or spectators they will all share a
	reference to a single global game.

	When a replay or raw log file is uploaded the server first checks
	for the existence of a GlobalGame record. It looks for any games
	that occured on the same region where both players have matching
	battle_net_ids and where the match start timestamp is within +/- 1
	minute from the timestamp on the upload.
	The +/- range on the match start timestamp is to account for
	potential clock drift between the computer that generated this
	replay and the computer that uploaded the earlier record which
	first created the GlobalGame record. If no existing GlobalGame
	record is found, then one is created.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

	# We believe game_id is not monotonically increasing as it appears
	# to roll over and reset periodically.
	game_server_game_id = models.IntegerField("Battle.net Game ID",
		null=True, blank=True,
		help_text="This is the game_id from the Net.log"
	)
	game_server_address = models.GenericIPAddressField(null=True, blank=True)
	game_server_port = models.IntegerField(null=True, blank=True)

	hearthstone_build = models.CharField("Hearthstone Build Number",
		max_length=50, blank=True, null=True,
		help_text="Patch number at the time the game was played."
	)

	match_start_timestamp = models.DateTimeField("Match Start Timestamp",
		help_text="Must be a timezone aware datetime."
	)

	match_end_timestamp = models.DateTimeField("Match End Timestamp",
		help_text="Must be a timezone aware datetime."
	)

	# The BnetGameType enum encodes whether it's ranked or casual as well as standard or wild.
	game_type = IntEnumField("Game Type",
		enum=BnetGameType,
		null=True, blank=True,
	)

	# ladder_season is nullable since not all games are ladder games
	ladder_season = models.IntegerField("Ladder season",
		null=True, blank=True,
		help_text="The season as calculated from the match start timestamp."
	)

	# Nullable, since not all replays are TBs.
	# Will currently have no way to calculate this so it will always be null for now.
	brawl_season = models.IntegerField("Tavern Brawl Season",
		default=0,
		help_text="The brawl season which increments every week the brawl changes."
	)

	# Nullable, We currently have no way to discover this.
	scenario_id = models.IntegerField("Scenario ID",
		null=True, blank=True,
		help_text="ID from DBF/SCENARIO.xml or Scenario cache",
	)

	# The following basic stats are globally visible to all
	num_turns = models.IntegerField()
	num_entities = models.IntegerField()

	class Meta:
		ordering = ("-match_start_timestamp", )

	def __str__(self):
		return " vs ".join(str(p) for p in self.players.all())

	@property
	def duration(self):
		return self.match_end_timestamp - self.match_start_timestamp

	@property
	def is_tavern_brawl(self):
		return self.game_type in (
			BnetGameType.BGT_TAVERNBRAWL_PVP,
			BnetGameType.BGT_TAVERNBRAWL_1P_VERSUS_AI,
			BnetGameType.BGT_TAVERNBRAWL_2P_COOP,
		)

	@property
	def num_own_turns(self):
		return ceil(self.num_turns / 2)


class GlobalGamePlayer(models.Model):
	game = models.ForeignKey(GlobalGame, related_name="players")

	name = models.CharField("Player name",
		blank=True, max_length=64,
	)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)

	player_id = PlayerIDField(null=True, blank=True)
	account_hi = models.BigIntegerField("Account Hi",
		blank=True, null=True,
		help_text="The region value from account hilo"
	)
	account_lo = models.BigIntegerField("Account Lo",
		blank=True, null=True,
		help_text="The account ID value from account hilo"
	)
	is_ai = models.BooleanField("Is AI",
		default=False,
		help_text="Whether the player is an AI.",
	)
	is_first = models.BooleanField("Is first player",
		help_text="Whether the player is the first player",
	)

	rank = models.SmallIntegerField("Rank",
		null=True, blank=True,
		help_text="1 through 25, or 0 for legend.",
	)
	legend_rank = models.PositiveIntegerField("Legend rank",
		null=True, blank=True,
	)

	hero = models.ForeignKey(Card)
	hero_premium = models.BooleanField("Hero Premium",
		default=False,
		help_text="Whether the player's initial hero is golden."
	)

	final_state = IntEnumField("Final State",
		enum=PlayState, default=PlayState.INVALID,
	)

	deck_list = models.ForeignKey(Deck,
		help_text="As much as is known of the player's starting deck list."
	)

	def __str__(self):
		return self.name

	@property
	def won(self):
		return self.final_state in (PlayState.WINNING, PlayState.WON)


class GameReplayUploadManager(models.Manager):
	def get_or_create_from_raw_log_upload(self, raw_log):
		"""
		Returns a tuple of the record and boolean indicating
		whether it was created.
		"""
		time_logger.info("TIMING: %s - Start of get_or_create_from_raw_log_upload" % _time_elapsed())
		# Don't attempt to create a replay if validation doesn't pass
		raw_log.full_clean()

		time_logger.info("TIMING: %s - About to read back raw log from S3" % _time_elapsed())

		raw_log.log.open(mode="rb")
		log = StringIO(raw_log.log.read().decode("utf-8"))
		raw_log.log.close()
		time_logger.info("TIMING: %s - Finished opening raw log. Generating packet tree..." % _time_elapsed())
		packet_tree = parse_log(log, processor="GameState", date=raw_log.match_start_timestamp)
		time_logger.info("TIMING: %s - Finished generating packet tree." % _time_elapsed())

		if not len(packet_tree.games):
			# We were not able to generate a replay
			raise ValidationError("Could not parse a replay from the raw log data")
		if len(packet_tree.games) > 1:
			raise NotImplementedError("Uploading multiple games in one log is unsupported.")

		game_tree = packet_tree.games[0]

		replay_tree = create_document(version=hsreplay_version, build=raw_log.hearthstone_build)

		time_logger.info("TIMING: %s - About to invoke game_to_xml" % _time_elapsed())
		player_meta = raw_log._generate_player_meta_data()
		game = game_to_xml(game_tree,
			game_meta = raw_log._generate_game_meta_data(),
			player_meta = player_meta,
			decks = raw_log._generate_deck_lists()
		)
		time_logger.info("TIMING: %s - game_to_xml Finished" % _time_elapsed())

		replay_tree.append(game)

		match_start_timestamp = game_tree.start_time
		match_end_timestamp = game_tree.end_time

		global_game = GlobalGame.objects.filter(
			game_server_address = raw_log.game_server_address,
			game_server_port = raw_log.game_server_port,
			game_server_game_id = raw_log.game_server_game_id,
			match_start_timestamp = match_start_timestamp,
			match_end_timestamp = match_end_timestamp,
		).first()

		if global_game:
			# If a global_game already exists then there is a possibility
			# that this is a duplicate upload, so check for it.
			existing = GameReplayUpload.objects.filter(
				global_game = global_game,
				is_spectated_game = raw_log.is_spectated_game,
				game_server_client_id = raw_log.game_server_client_id,
			).first()
			if existing:
				return existing, False

		friendly_player_id = raw_log.friendly_player_id or find_friendly_player(game_tree)
		if not friendly_player_id:
			raise ValidationError("Friendly player ID not present at upload and could not guess it.")

		num_entities = max(e.id for e in packet_tree.games[0].entities)
		num_turns = packet_tree.games[0].tags.get(GameTag.TURN)

		global_game = GlobalGame.objects.create(
			game_server_game_id = raw_log.game_server_game_id,
			game_server_address = raw_log.game_server_address,
			game_server_port = raw_log.game_server_port,
			game_type = raw_log.game_type,
			hearthstone_build = raw_log.hearthstone_build,
			match_start_timestamp = match_start_timestamp,
			match_end_timestamp = match_end_timestamp,
			ladder_season = self._current_season_number(match_start_timestamp),
			scenario_id = raw_log.scenario_id,
			num_entities = num_entities,
			num_turns = num_turns,
		)

		user = raw_log.upload_token.user

		replay = GameReplayUpload(
			friendly_player_id = friendly_player_id,
			game_server_client_id = raw_log.game_server_client_id,
			game_server_spectate_key = raw_log.game_server_spectate_key,
			global_game = global_game,
			hsreplay_version = hsreplay_version,
			is_spectated_game = raw_log.is_spectated_game,
			raw_log = raw_log,
			upload_timestamp = raw_log.upload_timestamp,
			user = user,
		)

		if user is None:
			# If the auth token has not yet been claimed, create
			# a pending claim for the replay for when it will be.
			claim = PendingReplayOwnership(replay=replay, token=raw_log.upload_token)
			claim.save()

		for player in replay_tree.iter("Player"):
			player_id = player.get("playerID")
			if player_id not in ("1", "2"):
				raise ValidationError("Unexpected player ID: %r" % (player_id))
			player_id = int(player_id)
			idx = player_id - 1

			account_lo, account_hi = player.get("accountLo"), player.get("accountHi")
			if not account_lo.isdigit():
				raise ValidationError("Unexpected accountLo: %r" % (account_lo))
			if not account_hi.isdigit():
				raise ValidationError("Unexpected accountHi: %r" % (account_hi))
			account_lo, account_hi = int(account_lo), int(account_hi)

			player_obj = game_tree.players[idx]
			hero = list(player_obj.heroes)[0]
			deck_list = self._get_starting_deck_list_for_player(idx, packet_tree, raw_log)
			final_state = player_obj.tags.get(GameTag.PLAYSTATE, 0)

			game_player = GlobalGamePlayer(
				game = global_game,
				player_id = player_id,
				name = player_obj.name,
				account_hi = account_hi,
				account_lo = account_lo,
				is_ai = account_lo == 0,
				hero_id = hero.card_id,
				hero_premium = hero.tags.get(GameTag.PREMIUM, False),
				rank = player_meta[idx].get("rank"),
				legend_rank = player_meta[idx].get("legendRank", 0),
				is_first = player_obj.tags.get(GameTag.FIRST_PLAYER, False),
				final_state = final_state,
				deck_list = deck_list,
			)
			game_player.save()

			if player_id == friendly_player_id:
				# Record whether the uploader won/lost that game
				if final_state in (PlayState.PLAYING, PlayState.INVALID):
					# This means we disconnected during the game
					replay.disconnected = True
				elif final_state in (PlayState.WINNING, PlayState.WON):
					replay.won = True
				else:
					# Anything else is a concede/loss/tie
					replay.won = False

		time_logger.info("TIMING: %s - About to generate XML." % _time_elapsed())
		xml_str = toxml(replay_tree, pretty=False)
		time_logger.info("TIMING: %s - Generate XML finished." % _time_elapsed())
		time_logger.info("TIMING: %s - About to call replay.replay_xml.save." % _time_elapsed())
		replay.replay_xml.save("hsreplay.xml", ContentFile(xml_str), save=False)
		time_logger.info("TIMING: %s - replay.replay_xml.save finished." % _time_elapsed())
		time_logger.info("TIMING: %s - About to call replay.save()" % _time_elapsed())
		replay.save()
		time_logger.info("TIMING: %s - replay.save() finished." % _time_elapsed())

		return replay, True

	def _get_starting_deck_list_for_player(self, num, packet_tree, raw_log):
		# If the raw_log has a deck_list then the client has uploaded
		# a complete 30 card list which takes precedence.
		starting_deck_card_ids = None
		if num == 0:
			if raw_log.player_1_deck_list:
				starting_deck_card_ids = raw_log.player_1_deck_list.split(",")
			else:
				starting_deck_card_ids = [e.card_id for e in packet_tree.games[0].players[num].initial_deck if e.card_id]
			deck, created = Deck.objects.get_or_create_from_id_list(starting_deck_card_ids)
			return deck

		if num == 1:
			if raw_log.player_2_deck_list:
				starting_deck_card_ids = raw_log.player_2_deck_list.split(",")
			else:
				starting_deck_card_ids = [e.card_id for e in packet_tree.games[0].players[num].initial_deck if e.card_id]
			deck, created = Deck.objects.get_or_create_from_id_list(starting_deck_card_ids)
			return deck

	def _current_season_number(self, match_start_timestamp):
		# Using Jan'2016 as a psuedo-epoch start since we know that is season 22
		epoch_start = datetime(2016, 1, 1)
		epoch_start_season = 22

		delta_months = (match_start_timestamp.year - epoch_start.year) * 12 + (match_start_timestamp.month - epoch_start.month)
		return epoch_start_season + delta_months


class GameReplayUpload(models.Model):
	"""
	Represents a replay as captured from the point of view of a single
	packet stream sent to a Hearthstone client.

	Replays can be uploaded by either of the players or by any number
	of spectators who watched the match. It is possible
	that the same game could be uploaded from multiple points of view.
	When this happens each GameReplayUpload will point
	to the same GlobalGame record via the global_game foreign key.

	It is possible that different uploads of the same game will have
	different information in them.
	For example:
	- If Player A and Player B are Real ID Friends and Player C is
	Battle.net friends with just Player B, then when Player C spectates
	a match between Players A and B, his uploaded replay will show the
	BattleTag as the name of Player A. However if Player B uploads a
	replay of the same match, his replay will show the real name for
	Player A.

	- Likewise, if Player C either starts spectating the game after it has
	already begun or stops spectating before it ends, then his uploaded
	replay will have fewer turns of gameplay then Player B's replay.
	"""
	class Meta:
		ordering = ("global_game", )
		unique_together = ("upload_token", "global_game")

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	objects = GameReplayUploadManager()
	upload_token = models.ForeignKey("api.AuthToken", null=True, blank=True, related_name="replays")
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
	upload_timestamp = models.DateTimeField()
	global_game = models.ForeignKey(GlobalGame,
		related_name="replays",
		help_text="References the single global game that this replay shows."
	)

	# raw_log can be null because a user might upload the XML of a replay directly.
	raw_log = models.ForeignKey(SingleGameRawLogUpload, related_name="replays", null=True)

	# This is useful to know because replays that are spectating both players
	# will have more data then those from a single player.
	# For example, they will have access to the cards that are in each players hand.
	# This is detectable from the raw logs, although we currently intend to have
	# the client uploading the replay provide it.
	is_spectated_game = models.BooleanField(default=False)

	# The "friendly player" is the player whose cards are at the bottom of the
	# screen when watching a game. For spectators this is determined by which
	# player they started spectating first (if they spectate both).
	friendly_player_id = PlayerIDField("Friendly Player ID",
		null=True,
		help_text="PlayerID of the friendly player (1 or 2)",
	)

	# This information is all optional and is from the Net.log ConnectAPI
	game_server_spectate_key = models.CharField(max_length=50, null=True, blank=True)
	game_server_client_id = models.IntegerField(null=True, blank=True)

	replay_xml = models.FileField(upload_to=_generate_replay_upload_key)
	hsreplay_version = models.CharField("HSReplay version",
		max_length=20,
		help_text="The HSReplay spec version of the HSReplay XML file",
	)

	# The fields below capture the preferences of the user who uploaded it.
	is_deleted = models.BooleanField("Soft deleted",
		default=False,
		help_text="Indicates user request to delete the upload"
	)
	exclude_in_aggregate_stats = models.BooleanField(default=False)

	won = models.NullBooleanField()
	disconnected = models.BooleanField(default=False)

	def __str__(self):
		players = self.global_game.players.values_list("player_id", "final_state", "name")
		if len(players) != 2:
			return "Incomplete game (%i players)" % (len(players))
		if players[0][0] == self.friendly_player_id:
			friendly, opponent = players
		else:
			opponent, friendly = players
		if self.disconnected:
			state = "Disconnected"
		elif self.won:
			state = "Won"
		elif friendly[1] == opponent[1]:
			state = "Tied"
		else:
			state = "Lost"
		return "%s (%s) vs %s" % (friendly[2], state, opponent[2])

	def get_absolute_url(self):
		return reverse("games_replay_view", kwargs={"id": self.id})

	@property
	def css_classes(self):
		ret = []
		if self.won is not None:
			if self.won:
				ret.append("hsreplay-positive")
			else:
				ret.append("hsreplay-negative")
		if self.disconnected:
			ret.append("hsreplay-invalid")
		return " ".join(ret)


class PendingReplayOwnership(models.Model):
	"""
	A model associating an AuthKey with a GameReplayUpload, until
	the AuthKey gains a real user.
	"""
	replay = models.OneToOneField(GameReplayUpload)
	token = models.ForeignKey("api.AuthToken", related_name="replay_claims")

	class Meta:
		unique_together = ("replay", "token")
