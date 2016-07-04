from django.core.management.base import BaseCommand, CommandError
from hsreplaynet.api.models import APIKey
from hsreplaynet.uploads.models import UploadEventStatus


class Command(BaseCommand):
	help = "Deletes all AuthTokens and the games uploaded with them for the provided API Key."

	def add_arguments(self, parser):
		parser.add_argument("api_key", help="The target API Key to be cleaned up")

	def handle(self, *args, **options):
		api_key_id = options["api_key"]
		try:
			api_key = APIKey.objects.get(api_key=api_key_id)
		except (APIKey.DoesNotExist, ValueError):
			raise CommandError("No such API Key: %r" % (api_key_id))
		self.stdout.write("Cleaning up %r" % (api_key))
		tokens = api_key.tokens.all()

		for token in tokens:
			self.stdout.write("\tDeleting uploads for %r" % (token))
			uploads = token.uploads.all()

			for upload in uploads:
				if upload.is_processing:
					self.stdout.write("\t\tSkipping %r (status=%r)" % (upload, upload.status))
					continue

				if upload.game:
					self.stdout.write("Deleting %r" % (upload.game))

					self.stdout.write("First checking the Global Game...")
					global_game = upload.game.global_game
					if global_game.replays.count() == 1:
						self.stdout.write("Nothing else references this Global Game. It will be deleted.")
						# The only replay associated with this global game is the one we are about to delete.
						# Thus, we also delete the global game to avoid leaving artifacts behind in the DB.
						global_game.delete()
					else:
						self.stdout.write("Other replays use this global game. It will not be deleted.")

					upload.game.delete()
				elif upload.status == UploadEventStatus.SUCCESS:
					msg = "WARNING: status=SUCCESS but no replay attached on %r" % (upload)
					raise CommandError(msg)
				else:
					self.stdout.write("No replays found.")

			uploads.delete()
		self.stdout.write("Deleting %i tokens" % (tokens.count()))
		tokens.delete()

		self.stdout.write("Done.")
