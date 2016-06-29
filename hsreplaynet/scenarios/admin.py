from django.contrib import admin
from .models import Adventure, Wing, Scenario


@admin.register(Adventure)
class AdventureAdmin(admin.ModelAdmin):
	list_display = ("__str__", "note_desc")
	list_filter = ("leaving_soon", )
	search_fields = ("name", "note_desc")


@admin.register(Wing)
class WingAdmin(admin.ModelAdmin):
	list_display = (
		"__str__", "adventure", "release", "required_event", "note_desc",
		"ownership_prereq_wing", "coming_soon_label", "requires_label"
	)
	list_filter = ("adventure", )
	search_fields = ("name", "note_desc")


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
	list_display = (
		"__str__", "note_desc", "is_tutorial", "is_expert", "is_coop",
		"players", "adventure", "wing", "mode", "opponent_name",
	)
	list_filter = ("players", "is_tutorial", "is_expert", "is_coop", "mode")
	search_fields = ("name", "note_desc", "description", "opponent_name")
