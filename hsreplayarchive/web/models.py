from django.db import models
import uuid


class HSReplayFile(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	data = models.BinaryField()


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


