from django.contrib import admin
from .models import *


@admin.register(GameReplayUpload)
class GameReplayUploadAdmin(admin.ModelAdmin):
	date_hierarchy = "upload_timestamp"
	list_display = (
		"__str__", "upload_timestamp", "global_game",
		"hsreplay_version", "replay_xml", "raw_log",
	)
	list_filter = ("is_spectated_game", "hsreplay_version")
	raw_id_fields = (
		"upload_token", "global_game", "raw_log",
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

@admin.register(GlobalGamePlayer)
class GlobalGamePlayerAdmin(admin.ModelAdmin):
	list_display = ("__str__", "user", "player_id", "is_first")
	list_filter = ("is_ai", "rank", "is_first")


@admin.register(SingleGameRawLogUpload)
class SingleGameRawLogUploadAdmin(admin.ModelAdmin):
	date_hierarchy = "match_start_timestamp"
	list_display = (
		"__str__", "upload_token", "match_start_timestamp", "hearthstone_build",
		"game_type", "scenario_id", "is_spectated_game"
	)
	list_filter = ("is_spectated_game", "game_type", "hearthstone_build")
	raw_id_fields = ("upload_token", )


@admin.register(SingleSiteUploadToken)
class SingleSiteUploadTokenAdmin(admin.ModelAdmin):
	list_display = ("__str__", "user", "created", "requested_by_upload_agent")
	raw_id_fields = ("user", )


@admin.register(UploadAgentAPIKey)
class UploadAgentAPIKeyAdmin(admin.ModelAdmin):
	list_display = ("__str__", "email", "website", "api_key")
	search_fields = ("full_name", "email", "website")
