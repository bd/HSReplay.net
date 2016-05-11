from django.core.management.base import BaseCommand
from cards.models import *


class Command(BaseCommand):

	def handle(self, *args, **options):

		Faction.objects.all().delete()
		PlayerClass.objects.all().delete()
		Type.objects.all().delete()
		Race.objects.all().delete()
		Collection.objects.all().delete()
		Rarity.objects.all().delete()
		Mechanic.objects.all().delete()
		Card.objects.all().delete()
