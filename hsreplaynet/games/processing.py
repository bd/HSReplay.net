import json
import logging
import traceback
from io import StringIO
from dateutil.parser import parse as dateutil_parse
from django.core.exceptions import ValidationError
from hearthstone.enums import GameTag
from hsreplay.dumper import parse_log
from hsreplaynet.cards.models import Deck
from hsreplaynet.utils import deduplication_time_range, guess_ladder_season
from hsreplaynet.utils.instrumentation import influx_metric
from hsreplaynet.uploads.models import UploadEventStatus
from .models import GameReplay, GlobalGame, GlobalGamePlayer, PendingReplayOwnership


logger = logging.getLogger(__file__)


class ProcessingError(Exception):
	pass


class ParsingError(ProcessingError):
	pass


class UnsupportedReplay(ProcessingError):
	pass


def eligible_for_unification(meta):
	return all([meta.get("game_id"), meta.get("client_id")])


def find_or_create_global_game(game_tree, meta):
	build = meta["build"]
	if build is None and "stats" in meta:
		build = meta["stats"]["meta"]["build"]
	game_id = meta.get("game_id")
	game_type = meta.get("game_type", 0)
	start_time = game_tree.start_time
	end_time = game_tree.end_time
	if "stats" in meta and "ranked_season_stats" in meta["stats"]:
		ladder_season = meta["stats"]["ranked_season_stats"]["season"]
	else:
		ladder_season = guess_ladder_season(end_time)

	global_game = None
	# Check if we have enough metadata to deduplicate the game
	if eligible_for_unification(meta):
		matches = GlobalGame.objects.filter(
			build=build,
			game_type=game_type,
			game_server_game_id=game_id,
			game_server_address=meta.get("server_ip"),
			game_server_port=meta.get("server_port"),
			match_start__range=deduplication_time_range(start_time),
		)

		if matches:
			if len(matches) > 1:
				# clearly something's up. invalidate the upload, look into it manually.
				raise ValidationError("Found too many global games. Mumble mumble...")
			return matches.first(), True

	global_game = GlobalGame.objects.create(
		game_server_game_id=game_id,
		game_server_address=meta.get("server_ip"),
		game_server_port=meta.get("server_port"),
		game_type=game_type,
		build=build,
		match_start=start_time,
		match_end=end_time,
		ladder_season=ladder_season,
		scenario_id=meta.get("scenario_id"),
		num_entities=len(game_tree.game.entities),
		num_turns=game_tree.game.tags.get(GameTag.TURN),
	)

	return global_game, False


def find_or_create_replay(global_game, meta, unified):
	client_id = meta.get("client_id")
	if unified:
		# Look for duplicate uploads
		replays = global_game.replays.filter(
			friendly_player_id=meta["friendly_player"],
			game_server_client_id=client_id,
		)
		if len(replays) > 1:
			raise RuntimeError("Found multiple client_id=%r for %r" % (client_id, global_game))
		elif replays:
			replay = replays.first()
			logger.info("Duplicate upload detected: %r", replay)
			return replay, True

	replay = GameReplay(
		global_game=global_game,
		friendly_player_id=meta["friendly_player"],
		game_server_client_id=client_id,
		game_server_spectate_key=meta.get("spectate_key"),
		is_spectated_game=meta.get("spectator_mode", False),
		reconnecting=meta.get("reconnecting", False),
	)

	return replay, False


def process_upload_event(upload_event):
	"""
	Wrapper around do_process_upload_event() to set the event's
	status and error/traceback as needed.
	"""
	upload_event.status = UploadEventStatus.PROCESSING
	upload_event.save()

	try:
		replay = do_process_upload_event(upload_event)
	except Exception as e:
		if isinstance(e, ParsingError):
			upload_event.status = UploadEventStatus.PARSING_ERROR
		elif isinstance(e, UnsupportedReplay):
			upload_event.status = UploadEventStatus.UNSUPPORTED
		else:
			upload_event.status = UploadEventStatus.SERVER_ERROR
		upload_event.error = str(e)
		upload_event.traceback = traceback.format_exc()
		upload_event.save()
		raise
	else:
		upload_event.game = replay
		upload_event.status = UploadEventStatus.SUCCESS
		upload_event.save()

	return replay


def parse_upload_event(upload_event, meta):
	match_start = dateutil_parse(meta["match_start"])
	upload_event.file.open(mode="rb")
	log = StringIO(upload_event.file.read().decode("utf-8"))
	upload_event.file.close()

	try:
		parser = parse_log(log, processor="GameState", date=match_start)
	except Exception as e:
		raise ParsingError(str(e))  # from e

	return parser


def validate_parser(parser, meta):
	# Validate upload
	if len(parser.games) != 1:
		raise ValidationError("Expected exactly 1 game, got %i" % (len(parser.games)))
	game_tree = parser.games[0]

	# If a player's name is None, this is an unsupported replay.
	for player in game_tree.game.players:
		if player.name is None:
			raise UnsupportedReplay("Could not extract player information from the log.")

	if not meta.get("friendly_player"):
		id = game_tree.guess_friendly_player()
		if not id:
			raise ValidationError("Friendly player ID not present at upload and could not guess it.")
		meta["friendly_player"] = id

	return game_tree


def get_player_names(player):
	if not player.is_ai and " " in player.name:
		return "", player.name
	else:
		return player.name, ""


def create_global_players(global_game, game_tree, meta):
	# Fill the player metadata and objects
	for player in game_tree.game.players:
		player_meta = meta.get("player%i" % (player.player_id), {})
		hero = list(player.heroes)[0]
		decklist = player_meta.get("deck")
		if not decklist:
			decklist = [c.card_id for c in player.initial_deck if c.card_id]
		deck, _ = Deck.objects.get_or_create_from_id_list(decklist)
		final_state = player.tags.get(GameTag.PLAYSTATE, 0)

		name, real_name = get_player_names(player)

		game_player = GlobalGamePlayer(
			game=global_game,
			player_id=player.player_id,
			name=name,
			real_name=real_name,
			account_hi=player.account_hi,
			account_lo=player.account_lo,
			is_ai=player.is_ai,
			hero_id=hero.card_id,
			hero_premium=hero.tags.get(GameTag.PREMIUM, False),
			rank=player_meta.get("rank"),
			legend_rank=player_meta.get("legend_rank"),
			stars=player_meta.get("stars"),
			wins=player_meta.get("wins"),
			losses=player_meta.get("losses"),
			is_first=player.tags.get(GameTag.FIRST_PLAYER, False),
			final_state=final_state,
			deck_list=deck,
		)

		game_player.save()


def update_global_players(global_game, game_tree, meta):
	logger.info("Unified upload. Updating players not implemented yet.")


def do_process_upload_event(upload_event):
	meta = json.loads(upload_event.metadata)
	parser = parse_upload_event(upload_event, meta)
	game_tree = validate_parser(parser, meta)
	global_game, unified = find_or_create_global_game(game_tree, meta)
	if upload_event.game:
		replay, duplicate = upload_event.game, True
	else:
		replay, duplicate = find_or_create_replay(global_game, meta, unified)

	if unified or duplicate:
		update_global_players(global_game, game_tree, meta)
	else:
		create_global_players(global_game, game_tree, meta)

	user = upload_event.token.user if upload_event.token else None
	if user and not replay.user:
		replay.user = user

	# Create and save hsreplay.xml file
	file = replay.save_hsreplay_xml(parser, meta)
	influx_metric("replay_xml_num_bytes", {"size": file.size})
	replay.update_final_states()
	replay.save()

	# Manual uploads (admin/command line) don't have tokens attached
	if user is None and upload_event.token is not None:
		# If the auth token has not yet been claimed, create
		# a pending claim for the replay for when it will be.
		claim = PendingReplayOwnership(replay=replay, token=upload_event.token)
		claim.save()

	return replay
