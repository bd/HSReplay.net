from django.core.management.base import BaseCommand
from hearthstone import cardxml
from ...models import Card


class Command(BaseCommand):
	def handle(self, *args, **options):
		db, _ = cardxml.load()
		created = 0

		self.stdout.write("%i cards available" % (len(db)))

		for card in db.values():
			obj, created = Card.objects.get_or_create_from_cardxml(card)
			if created:
				self.stdout.write("New card: %r (%s)" % (obj, obj.id))
				created += 1

		self.stdout.write("%i new cards" % (created))
