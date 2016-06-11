import json
from io import StringIO
from dateutil.parser import parse as dateutil_parse
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from hearthstone.enums import GameTag, PlayState, PowerType, Zone
from hsreplay import __version__ as hsreplay_version
from hsreplay.dumper import parse_log, create_document, game_to_xml
from hsreplay.utils import toxml
from hsreplaynet.utils import deduplication_time_range, guess_ladder_season
from hsreplaynet.cards.models import Deck
from hsreplaynet.uploads.models import UploadEventStatus
from .models import GameReplay, GlobalGame, GlobalGamePlayer, PendingReplayOwnership


def _get_player_meta(d, i):
	player = d["player%i" % (i)]
	return {
		"rank": str(player["rank"]),
		"legendRank": str(player["legend_rank"]),
		"cardback": str(player["cardback"]),
	}


def find_friendly_player(game_tree):
	for packet in game_tree.packets[1:]:
		if packet.type != PowerType.FULL_ENTITY:
			break
		tags = dict(packet.tags)
		if tags[GameTag.ZONE] == Zone.HAND and not packet.cardid:
			return tags[GameTag.CONTROLLER] % 2 + 1


def eligible_for_unification(meta):
	return False


def find_duplicate_games(meta, timestamp):
	matches = GlobalGame.objects.filter(
		hearthstone_build = meta["hearthstone_build"],
		game_type = meta["game_type"],
		game_server_game_id = meta["game_id"],
		game_server_address = meta["server_ip"],
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

	upload_event.file.open(mode="rb")
	log = StringIO(upload_event.file.read().decode("utf-8"))
	upload_event.file.close()

	match_start_timestamp = dateutil_parse(meta["match_start_timestamp"])
	packet_tree = parse_log(log, processor="GameState", date=match_start_timestamp)

	if len(packet_tree.games) != 1:
		raise ValidationError("Expected exactly 1 game, got %i" % (len(packet_tree.games)))

	game_tree = packet_tree.games[0]

	build = meta["hearthstone_build"] or meta["stats"]["meta"]["hearthstone_build"]
	root = create_document(version=hsreplay_version, build=build)
	player_meta = [_get_player_meta(meta, i) for i in (1, 2)]
	game_meta = {
		"id": str(meta["game_id"]),
		"type": str(meta["game_type"]),
		"reconnecting": str(meta["reconnecting"]).lower(),
	}
	# decks = [deck.split(",") for deck in meta["decks"]]
	game = game_to_xml(game_tree,
		game_meta = game_meta,
		player_meta = player_meta,
		decks = [meta.get("player1", {}).get("deck"), meta.get("player2", {}).get("deck")],
	)
	root.append(game)

	start_time = game_tree.start_time
	end_time = game_tree.end_time
	if "stats" in meta and "ranked_season_stats" in meta["stats"]:
		ladder_season = meta["stats"]["ranked_season_stats"]["season"]
	else:
		ladder_season = guess_ladder_season(end_time)

	friendly_player_id = meta.get("friendly_player") or find_friendly_player(game_tree)
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
		num_entities = max(e.id for e in packet_tree.games[0].entities)
		num_turns = packet_tree.games[0].tags.get(GameTag.TURN)

		global_game = GlobalGame.objects.create(
			game_server_game_id = meta["game_id"],
			game_server_address = meta["server_ip"],
			game_server_port = meta["server_port"],
			game_type = meta["game_type"],
			hearthstone_build = build,
			match_start_timestamp = start_time,
			match_end_timestamp = end_time,
			ladder_season = ladder_season,
			scenario_id = meta["scenario_id"],
			num_entities = num_entities,
			num_turns = num_turns,
		)

	if not upload_event.token:
		raise ValidationError("No token attached to upload event %r" % (upload_event))
	user = upload_event.token.user

	replay = GameReplay(
		friendly_player_id = friendly_player_id,
		game_server_client_id = meta["client_id"],
		game_server_spectate_key = meta["spectate_key"],
		global_game = global_game,
		hsreplay_version = hsreplay_version,
		is_spectated_game = meta["spectator_mode"],
		# raw_log = raw_log,
		user = user,
	)

	for player in root.iter("Player"):
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
		decklist = meta["player%i_deck" % (player_id)]
		if not decklist:
			decklist = [c.card_id for c in player_obj.initial_deck if c.card_id]
		deck, _ = Deck.objects.get_or_create_from_id_list(decklist)
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
			deck_list = deck,
			duplicated = unifying,
		)
		game_player.save()

		# XXX move the following to replay save()
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

	xml_str = toxml(root, pretty=False)
	replay.replay_xml.save("hsreplay.xml", ContentFile(xml_str), save=False)
	replay.save()

	if user is None:
		# If the auth token has not yet been claimed, create
		# a pending claim for the replay for when it will be.
		claim = PendingReplayOwnership(replay=replay, token=upload_event.token)
		claim.save()

	upload_event.status = UploadEventStatus.SUCCESS
	upload_event.save()

	return replay
