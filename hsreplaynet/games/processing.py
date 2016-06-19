import json
from io import StringIO
from dateutil.parser import parse as dateutil_parse
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from hearthstone.enums import BnetGameType, GameTag, PlayState
from hsreplay.document import HSReplayDocument
from hsreplay.dumper import parse_log
from hsreplaynet.utils import deduplication_time_range, guess_ladder_season
from hsreplaynet.cards.models import Deck
from hsreplaynet.uploads.models import UploadEventStatus
from hsreplaynet.utils import instrumentation
from .models import GameReplay, GlobalGame, GlobalGamePlayer, PendingReplayOwnership


def eligible_for_unification(meta):
	return False


def find_duplicate_games(meta, timestamp):
	matches = GlobalGame.objects.filter(
		hearthstone_build = meta["hearthstone_build"],
		game_type = meta["game_type"],
		game_server_game_id = meta["game_id"],
		game_server_address = meta.get("server_ip"),
		game_server_port = meta["server_port"],
		match_start_timestamp__range = deduplication_time_range(timestamp),
	)

	if matches:
		if len(matches) > 1:
			# clearly something's up. invalidate the upload, look into it manually.
			raise ValidationError("Found too many global games. Mumble mumble...")
		global_game = matches.first()

		# Check for duplicate uploads of the same game (eg. from same POV)
		uploads = GameReplay.objects.filter(
			global_game = global_game,
			is_spectated_game = meta["spectator_mode"],
			game_server_client_id = meta["client_id"],
		)
		if len(uploads) > 1:
			raise ValidationError("Found too many player games... What happened?")
		elif uploads:
			return global_game, uploads.first()
	return global_game, None


def process_upload_event(upload_event):
	if upload_event.game:
		raise NotImplementedError("Reprocessing not implemented yet")
	upload_event.status = UploadEventStatus.PROCESSING
	upload_event.save()

	meta = json.loads(upload_event.metadata)
	match_start_timestamp = dateutil_parse(meta["match_start_timestamp"])
	game_type = meta.get("game_type", BnetGameType.BGT_UNKNOWN)
	game_id = meta.get("game_id")
	reconnecting = meta.get("reconnecting", False)
	build = meta["hearthstone_build"] or meta["stats"]["meta"]["hearthstone_build"]

	upload_event.file.open(mode="rb")
	log = StringIO(upload_event.file.read().decode("utf-8"))
	upload_event.file.close()

	parser = parse_log(log, processor="GameState", date=match_start_timestamp)

	if len(parser.games) != 1:
		raise ValidationError("Expected exactly 1 game, got %i" % (len(parser.games)))
	game_tree = parser.games[0]

	start_time = game_tree.start_time
	end_time = game_tree.end_time
	if "stats" in meta and "ranked_season_stats" in meta["stats"]:
		ladder_season = meta["stats"]["ranked_season_stats"]["season"]
	else:
		ladder_season = guess_ladder_season(end_time)

	friendly_player_id = meta.get("friendly_player") or game_tree.guess_friendly_player()
	if not friendly_player_id:
		raise ValidationError("Friendly player ID not present at upload and could not guess it.")

	# Check if we have enough metadata to deduplicate the game
	unifying = False
	if eligible_for_unification(meta):
		global_game, upload = find_duplicate_games(meta, start_time)
		if upload:
			return upload  # ?
		elif global_game:
			unifying = True

	if not unifying:
		num_entities = max(e.id for e in game_tree.game.entities)
		num_turns = game_tree.game.tags.get(GameTag.TURN)

		global_game = GlobalGame.objects.create(
			game_server_game_id=game_id,
			game_server_address=meta.get("server_ip"),
			game_server_port=meta.get("server_port"),
			game_type=game_type,
			hearthstone_build=build,
			match_start_timestamp=start_time,
			match_end_timestamp=end_time,
			ladder_season=ladder_season,
			scenario_id=meta.get("scenario_id"),
			num_entities=num_entities,
			num_turns=num_turns,
		)

	if upload_event.token:
		user = upload_event.token.user
	else:
		# No token was attached to the request (maybe a manual one?)
		user = None

	# Create the HSReplay document
	hsreplay_doc = HSReplayDocument.from_parser(parser, build=build)
	game_xml = hsreplay_doc.games[0]
	game_xml.game_type = game_type
	if game_id:
		game_xml.id = game_id
	if reconnecting:
		game_xml.reconnecting = True

	# The replay object in the db
	replay = GameReplay(
		friendly_player_id=friendly_player_id,
		game_server_client_id=meta.get("client_id"),
		game_server_spectate_key=meta.get("spectate_key"),
		global_game=global_game,
		hsreplay_version=hsreplay_doc.version,
		is_spectated_game=meta.get("spectator_mode", False),
		user=user,
	)

	# Fill the player metadata and objects
	for player in game_tree.game.players:
		player_meta_obj = meta.get("player%i" % (player.player_id), {})
		hero = list(player.heroes)[0]
		decklist = player_meta_obj.get("deck")
		if not decklist:
			decklist = [c.card_id for c in player.initial_deck if c.card_id]
		deck, _ = Deck.objects.get_or_create_from_id_list(decklist)
		final_state = player.tags.get(GameTag.PLAYSTATE, 0)

		player_xml = game_xml.players[player.player_id - 1]
		player_xml.rank = player_meta_obj.get("rank")
		player_xml.legendRank = player_meta_obj.get("legend_rank")
		player_xml.cardback = player_meta_obj.get("cardback")
		player_xml.deck = player_meta_obj.get("deck")

		game_player = GlobalGamePlayer(
			game=global_game,
			player_id=player.player_id,
			name=player.name,
			account_hi=player.account_hi,
			account_lo=player.account_lo,
			is_ai=player.is_ai,
			hero_id=hero.card_id,
			hero_premium=hero.tags.get(GameTag.PREMIUM, False),
			rank=player_meta_obj.get("rank"),
			legend_rank=player_meta_obj.get("legend_rank"),
			stars=player_meta_obj.get("stars"),
			wins=player_meta_obj.get("wins"),
			losses=player_meta_obj.get("losses"),
			is_first=player.tags.get(GameTag.FIRST_PLAYER, False),
			final_state=final_state,
			deck_list=deck,
			duplicated=unifying,
		)

		# XXX move the following to replay save()
		if player.player_id == friendly_player_id:
			# Record whether the uploader won/lost that game
			if final_state in (PlayState.PLAYING, PlayState.INVALID):
				# This means we disconnected during the game
				replay.disconnected = True
			elif final_state in (PlayState.WINNING, PlayState.WON):
				replay.won = True
			else:
				# Anything else is a concede/loss/tie
				replay.won = False

		game_player.save()

	# Save to XML
	xml_str = hsreplay_doc.to_xml()
	xml_file = ContentFile(xml_str)
	instrumentation.influx_metric("replay_xml_num_bytes", {"size": xml_file.size})
	replay.replay_xml.save("hsreplay.xml", xml_file, save=False)

	replay.save()

	if user is None and upload_event.token is not None:
		# If the auth token has not yet been claimed, create
		# a pending claim for the replay for when it will be.
		claim = PendingReplayOwnership(replay=replay, token=upload_event.token)
		claim.save()

	upload_event.game = replay
	upload_event.status = UploadEventStatus.SUCCESS
	upload_event.save()

	return replay
