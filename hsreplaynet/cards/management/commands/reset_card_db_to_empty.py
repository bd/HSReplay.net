from django.core.management.base import BaseCommand
from ...models import Card


class Command(BaseCommand):
	def handle(self, *args, **options):
		Card.objects.all().delete()
