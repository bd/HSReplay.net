from django.db import models


class StatsMeta(models.Model):
	hearthstone_build = models.PositiveIntegerField()
	platform = models.PositiveIntegerField(default=1)
	battlenet_id = models.BigIntegerField()
	region = models.PositiveSmallIntegerField()


class PlayerStats(models.Model):
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta)

	gold_progress = models.PositiveIntegerField()
	gold_balance = models.PositiveIntegerField()


class ArenaDraftStats(models.Model):
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta)

	wins = models.PositiveIntegerField()
	losses = models.PositiveIntegerField()
	deck_id = models.PositiveIntegerField()


class BrawlSeasonStats(models.Model):
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta)

	season = models.IntegerField()
	brawl = models.IntegerField()  # scenario id
	wins = models.IntegerField()
	played = models.PositiveIntegerField()
	streak = models.PositiveIntegerField()


class RankedSeasonStats(models.Model):
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta)

	wild = models.BooleanField()
	season = models.IntegerField()
	rank = models.PositiveIntegerField()
	stars = models.PositiveIntegerField()
	best_stars = models.PositiveIntegerField()
	wins = models.PositiveIntegerField()
	streak = models.PositiveIntegerField()
