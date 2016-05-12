from django.core.management.base import BaseCommand
from cards.models import Card


class Command(BaseCommand):
	def handle(self, *args, **options):
		Card.objects.all().delete()
