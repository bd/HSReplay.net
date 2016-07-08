import json
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from hsreplaynet.uploads.models import UploadEvent, UploadEventType


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument("file", nargs="+")

	def handle(self, *args, **options):
		for file in options["file"]:
			print("Uploading %r" % (file))
			metadata = {
				"build": 0,
				"match_start_timestamp": now().isoformat(),
			}

			event = UploadEvent(
				type=UploadEventType.POWER_LOG,
				upload_ip="127.0.0.1",
				metadata=json.dumps(metadata),
			)

			event.file = file
			event.save()

			with open(file, "r") as f:
				event.file = File(f)
				event.save()

			event.process()
			self.stdout.write("%r: %s" % (event, event.get_absolute_url()))
