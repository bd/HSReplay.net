from django.contrib import admin
from .models import *


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
	list_display = (
		"__str__", "id", "description", "card_set", "rarity", "type",
		"card_class", "artist"
	)
	list_filter = (
		"collectible", "card_set",
		"card_class", "type", "rarity", "cost",
		"battlecry", "deathrattle", "inspire",
		"divine_shield", "taunt", "windfury",
		"overload", "spell_damage"
	)
	search_fields = (
		"name", "description", "id",
	)


class IncludeInline(admin.TabularInline):
	model = Include
	raw_id_fields = ("card", )
	extra = 15


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
	date_hierarchy = "created"
	inlines = (IncludeInline, )
