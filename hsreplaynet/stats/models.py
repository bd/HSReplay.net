from django.db import models


class StatsMeta(models.Model):
	id = models.BigAutoField(primary_key=True)
	hearthstone_build = models.PositiveIntegerField()
	platform = models.PositiveIntegerField(default=1)
	battlenet_id = models.BigIntegerField()
	region = models.CharField(max_length=4)


class PlayerStats(models.Model):
	id = models.BigAutoField(primary_key=True)
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta, on_delete=models.CASCADE)

	gold_progress = models.PositiveIntegerField()
	gold_balance = models.PositiveIntegerField()


class ArenaDraftStats(models.Model):
	id = models.BigAutoField(primary_key=True)
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta, on_delete=models.CASCADE)

	wins = models.PositiveIntegerField()
	losses = models.PositiveIntegerField()
	deck_id = models.PositiveIntegerField()


class BrawlSeasonStats(models.Model):
	id = models.BigAutoField(primary_key=True)
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta, on_delete=models.CASCADE)

	season = models.IntegerField()
	brawl = models.IntegerField()  # scenario id
	wins = models.IntegerField()
	played = models.PositiveIntegerField()
	streak = models.PositiveIntegerField()


class RankedSeasonStats(models.Model):
	id = models.BigAutoField(primary_key=True)
	snapshot_time = models.DateTimeField()
	meta = models.ForeignKey(StatsMeta, on_delete=models.CASCADE)

	wild = models.BooleanField()
	season = models.IntegerField()
	rank = models.PositiveIntegerField()
	stars = models.PositiveIntegerField()
	best_stars = models.PositiveIntegerField()
	wins = models.PositiveIntegerField()
	streak = models.PositiveIntegerField()
