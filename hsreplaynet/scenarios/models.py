from enum import IntEnum
from django.db import models
from hsreplaynet.utils.fields import IntEnumField


class AdventureMode(IntEnum):
	# From ADVENTURE_MODE.xml
	NORMAL = 1
	EXPERT = 2
	HEROIC = 3
	CLASS_CHALLENGE = 4


class Adventure(models.Model):
	note_desc = models.CharField(max_length=64)
	name = models.CharField(max_length=64)
	sort_order = models.PositiveIntegerField(default=0)
	leaving_soon = models.BooleanField(default=False)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	build = models.PositiveIntegerField()

	def __str__(self):
		return self.name or self.note_desc


class Wing(models.Model):
	note_desc = models.CharField(max_length=64)
	adventure = models.ForeignKey(Adventure)
	sort_order = models.PositiveIntegerField()
	release = models.CharField(max_length=16)
	required_event = models.CharField(max_length=16)
	ownership_prereq_wing = models.ForeignKey("Wing", null=True, blank=True)
	name = models.CharField(max_length=64)
	coming_soon_label = models.CharField(max_length=64)
	requires_label = models.CharField(max_length=64)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	build = models.PositiveIntegerField()

	def __str__(self):
		return self.name or self.note_desc


class Scenario(models.Model):
	note_desc = models.CharField(max_length=64)
	players = models.PositiveSmallIntegerField()
	player1_hero_card_id = models.IntegerField(null=True)
	player2_hero_card_id = models.IntegerField(null=True)
	is_tutorial = models.BooleanField(default=False)
	is_expert = models.BooleanField(default=False)
	is_coop = models.BooleanField(default=False)
	adventure = models.ForeignKey(Adventure, null=True, blank=True)
	wing = models.ForeignKey(Wing, null=True, blank=True)
	sort_order = models.PositiveIntegerField(default=0)
	mode = IntEnumField(enum=AdventureMode, default=0)
	client_player2_hero_card_id = models.IntegerField()
	name = models.CharField(max_length=64)
	description = models.TextField()
	opponent_name = models.CharField(max_length=64)
	completed_description = models.TextField()
	player1_deck_id = models.IntegerField(null=True)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	build = models.PositiveIntegerField()

	def __str__(self):
		return self.name or self.note_desc
