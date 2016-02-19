from django.db import models
from django.core.urlresolvers import reverse
import uuid
from datetime import date


class HSReplaySingleGameFileUpload(models.Model):
	"""A user uploaded .hsreplay file containing only a single game.

	player_1 here means the player who goes first.
	player_2 here is the player with the coin.
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	data = models.BinaryField()
	upload_date = models.DateField(default=date.today)
	match_date = models.DateField(null=True)
	player_1_name = models.CharField(max_length=255, null=True)
	player_2_name = models.CharField(max_length=255, null=True)

	def get_absolute_url(self):
		return reverse('joust_replay_view', kwargs={'id':self.id})


# class HSReplayFileUpload:
# 	"""A .hsreplay file uploaded to the server
#
# 	Replays are stored in S3 by default as an object with the same UUID.
# 	"""
# 	uuid = None # This is the key to the object in the S3 bucket.
# 	upload_date = None # The date the file was uploaded.
# 	user = None # Once we have users we will want to track who is the owner of the object.
# 	game_count = None # The number of <Game> objects contained within the replay. Should be at least 1.
# 	version = None # The version of Hearthstone that this replay was generated against.
#
#
# class HSReplayGame:
# 	"""A single game from a .hsreplay file
#
# 	Uploaded .hsreplay files are parsed and synthetic .hsreplay files are generated for each individual game.
# 	"""
# 	id = None
# 	parent_replay_file = None
#
#
# 	@property
# 	def version(self):
# 		return None #This should be parent


