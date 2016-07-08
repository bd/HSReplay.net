from django.contrib import admin
from django.db.models import Count
from hsreplaynet.uploads.models import UploadEvent
from hsreplaynet.utils.admin import admin_urlify as urlify, set_user
from .models import GameReplay, GlobalGame, GlobalGamePlayer


class GlobalGamePlayerInline(admin.StackedInline):
	model = GlobalGamePlayer
	raw_id_fields = ("user", "deck_list")
	max_num = 2
	show_change_link = True


class UploadEventInline(admin.StackedInline):
	model = UploadEvent
	extra = 0
	raw_id_fields = ("token", )
	show_change_link = True


class GameReplayInline(admin.StackedInline):
	model = GameReplay
	extra = 0
	raw_id_fields = ("upload_token", "user")
	show_change_link = True


@admin.register(GameReplay)
class GameReplayAdmin(admin.ModelAdmin):
	actions = (set_user, )
	list_display = (
		"__str__", urlify("user"), urlify("global_game"),
		"hsreplay_version", "replay_xml",
	)
	list_filter = (
		"hsreplay_version", "is_spectated_game", "won", "disconnected",
		"is_deleted",
	)
	raw_id_fields = (
		"upload_token", "user", "global_game",
	)
	inlines = (UploadEventInline, )


class ReplaySidesFilter(admin.SimpleListFilter):
	"""
	A filter to look up the amount of uploads on a GlobalGame
	"""
	title = "replay sides"
	parameter_name = "sides"

	def lookups(self, request, model_admin):
		return (0, "0 (broken)"), (1, "1 (normal)"), (2, "2 (both sides)"), (3, "3+ (?)")

	def queryset(self, request, queryset):
		queryset = queryset.annotate(sides=Count("replays"))
		value = self.value()
		if value is not None and value.isdigit():
			value = int(value)
			if value > 2:
				return queryset.filter(sides__gt=2)
			return queryset.filter(sides__exact=value)
		return queryset


@admin.register(GlobalGame)
class GlobalGameAdmin(admin.ModelAdmin):
	date_hierarchy = "match_start_timestamp"
	list_display = (
		"__str__", "game_server_game_id", "game_type", "ladder_season",
		"brawl_season", "scenario_id", "num_turns", "num_entities",
	)
	list_filter = (
		"game_type", "ladder_season", "brawl_season", "build", ReplaySidesFilter
	)
	inlines = (GlobalGamePlayerInline, GameReplayInline)


@admin.register(GlobalGamePlayer)
class GlobalGamePlayerAdmin(admin.ModelAdmin):
	actions = (set_user, )
	list_display = ("__str__", urlify("user"), "player_id", "is_first")
	list_filter = ("is_ai", "rank", "is_first")
	raw_id_fields = ("game", "user", "deck_list")
