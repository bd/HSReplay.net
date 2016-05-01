from django.core.management.base import BaseCommand
from cards.loader import HearthstoneApiLoader
from cards.models import CardCollectionAuditLog
from datetime import date, datetime


class Command(BaseCommand):
	def handle(self, *args, **options):
		audit_log = CardCollectionAuditLog()
		audit_log.job_date = date.today()
		audit_log.card_collection_start = datetime.now()
		audit_log.save()

		try:
			loader = HearthstoneApiLoader()
			result = loader.load()
			audit_log.num_new_cards_loaded = result.num_new_cards_created
			audit_log.card_collection_succeeded = True
			audit_log.card_collection_end = datetime.now()
			audit_log.save()

		except Exception as e:

			audit_log.card_collection_succeeded = False
			audit_log.exception_text = str(e)
			audit_log.card_collection_end = datetime.now()
			audit_log.save()
