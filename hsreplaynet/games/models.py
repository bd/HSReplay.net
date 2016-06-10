from math import ceil
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.db import models
from hearthstone.enums import BnetGameType, PlayState
from hsreplaynet.cards.models import Card, Deck
from hsreplaynet.uploads.models import UploadEventStatus
from hsreplaynet.utils.fields import IntEnumField, PlayerIDField, ShortUUIDField


def _generate_replay_upload_key(instance, filename):
	timestamp = instance.global_game.match_start_timestamp.strftime("%Y/%m/%d")
	return "%s/replays/%s.xml" % (timestamp, str(instance.id))


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
	id = models.BigAutoField(primary_key=True)

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
	id = models.BigAutoField(primary_key=True)
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

	duplicated = models.BooleanField("Duplicated",
		default=False,
		help_text="Set to true if the player was created from a deduplicated upload."
	)

	def __str__(self):
		return self.name

	@property
	def won(self):
		return self.final_state in (PlayState.WINNING, PlayState.WON)


class GameReplayManager(models.Manager):
	def get_or_create_from_game_upload_event(self, game_upload_event):
		# meta_data = json.loads(game_upload_event.meta_data)
		# TODO: Use the metadata to generate the GameReplay record.
		# ...

		# NOTE: This method should update the status Enum on this object based on what happens inside this method.
		game_upload_event.status = UploadEventStatus.SUCCESS
		game_upload_event.save()

		# Callers of this method expect a tuple of the GameReplay and a Boolean to indicate whether it was created
		return (None, False)


class GameReplay(models.Model):
	"""
	Represents a replay as captured from the point of view of a single
	packet stream sent to a Hearthstone client.

	Replays can be uploaded by either of the players or by any number
	of spectators who watched the match. It is possible
	that the same game could be uploaded from multiple points of view.
	When this happens each GameReplay will point
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

	id = models.BigAutoField(primary_key=True)
	shortid = ShortUUIDField("Short ID")
	upload_token = models.ForeignKey("api.AuthToken", null=True, blank=True, related_name="replays")
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
	global_game = models.ForeignKey(GlobalGame,
		related_name="replays",
		help_text="References the single global game that this replay shows."
	)

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

	objects = GameReplayManager()

	def __str__(self):
		players = self.global_game.players.values_list("player_id", "final_state", "name")
		if len(players) != 2:
			return "Broken game (%i players)" % (len(players))
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
		return reverse("games_replay_view", kwargs={"id": self.shortid})

	def delete(self, using=None):
		# We must cleanup the S3 object ourselves (It is not handled by django-storages)
		if default_storage.exists(self.replay_xml.name):
			self.replay_xml.delete()

		return super(GameReplay, self).delete(using)

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
	A model associating an AuthKey with a GameReplay, until
	the AuthKey gains a real user.
	"""
	replay = models.OneToOneField(GameReplay)
	token = models.ForeignKey("api.AuthToken", related_name="replay_claims")

	class Meta:
		unique_together = ("replay", "token")
