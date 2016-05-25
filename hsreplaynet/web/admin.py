from django.contrib import admin
from hsreplaynet.utils import admin_urlify as urlify, set_user
from .models import *


class GlobalGamePlayerInline(admin.TabularInline):
	model = GlobalGamePlayer
	raw_id_fields = ("user", "deck_list")
	max_num = 2
	show_change_link = True


@admin.register(GameReplayUpload)
class GameReplayUploadAdmin(admin.ModelAdmin):
	actions = (set_user, )
	date_hierarchy = "upload_timestamp"
	list_display = (
		"__str__", urlify("user"), "upload_timestamp", urlify("global_game"),
		"hsreplay_version", "replay_xml", urlify("raw_log")
	)
	list_filter = (
		"hsreplay_version", "is_spectated_game", "won", "disconnected",
		"is_deleted", "exclude_in_aggregate_stats",
	)
	raw_id_fields = (
		"upload_token", "user", "global_game", "raw_log",
	)


@admin.register(GlobalGame)
class GlobalGameAdmin(admin.ModelAdmin):
	date_hierarchy = "match_start_timestamp"
	list_display = (
		"__str__", "game_server_game_id", "game_type", "ladder_season",
		"brawl_season", "scenario_id", "num_turns", "num_entities",
	)
	list_filter = (
		"game_type", "ladder_season", "brawl_season", "hearthstone_build"
	)
	inlines = (GlobalGamePlayerInline, )


@admin.register(GlobalGamePlayer)
class GlobalGamePlayerAdmin(admin.ModelAdmin):
	actions = (set_user, )
	list_display = ("__str__", urlify("user"), "player_id", "is_first")
	list_filter = ("is_ai", "rank", "is_first")
	raw_id_fields = ("game", "user", "deck_list")


@admin.register(SingleGameRawLogUpload)
class SingleGameRawLogUploadAdmin(admin.ModelAdmin):
	date_hierarchy = "match_start_timestamp"
	list_display = (
		"__str__", "upload_token", "match_start_timestamp", "hearthstone_build",
		"game_type", "scenario_id", "is_spectated_game"
	)
	list_filter = ("is_spectated_game", "game_type", "hearthstone_build")
	raw_id_fields = ("upload_token", )
