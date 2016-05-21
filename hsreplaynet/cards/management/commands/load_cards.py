from datetime import date
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from ...loader import CardXMLLoader
from ...models import CardCollectionAuditLog


class Command(BaseCommand):
	def handle(self, *args, **options):
		audit_log = CardCollectionAuditLog()
		audit_log.job_date = date.today()
		audit_log.card_collection_start = now()
		audit_log.save()

		try:
			loader = CardXMLLoader()
			result = loader.load()
			audit_log.num_new_cards_loaded = result.created
			audit_log.card_collection_succeeded = True
			audit_log.card_collection_end = now()
			audit_log.save()
		except Exception as e:
			audit_log.card_collection_succeeded = False
			audit_log.exception_text = str(e)
			audit_log.card_collection_end = now()
			audit_log.save()
