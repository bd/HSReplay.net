from django.contrib import admin
from .models import Adventure, Wing, Scenario


class ScenarioInline(admin.TabularInline):
	model = Scenario
	fields = ("name", "note_desc", "adventure", "wing", "mode")
	readonly_fields = fields
	extra = 0
	show_change_link = True


class WingInline(admin.TabularInline):
	model = Wing
	fields = (
		"name", "note_desc", "ownership_prereq_wing", "coming_soon_label"
	)
	readonly_fields = fields
	extra = 0
	show_change_link = True


@admin.register(Adventure)
class AdventureAdmin(admin.ModelAdmin):
	list_display = ("__str__", "note_desc")
	list_filter = ("leaving_soon", )
	search_fields = ("name", "note_desc")
	inlines = (WingInline, ScenarioInline, )


@admin.register(Wing)
class WingAdmin(admin.ModelAdmin):
	list_display = (
		"__str__", "adventure", "release", "required_event", "note_desc",
		"ownership_prereq_wing", "coming_soon_label", "requires_label"
	)
	list_filter = ("adventure", )
	search_fields = ("name", "note_desc")
	inlines = (ScenarioInline, )


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
	list_display = (
		"__str__", "note_desc", "is_tutorial", "is_expert", "is_coop",
		"players", "adventure", "wing", "mode", "opponent_name",
	)
	list_filter = (
		"adventure", "players", "is_tutorial", "is_expert", "is_coop", "mode"
	)
	search_fields = ("name", "note_desc", "description", "opponent_name")
