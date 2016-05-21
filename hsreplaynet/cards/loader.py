"""
Provides a loader for CardXML cards from python-hearthstone database
"""

from hearthstone import cardxml
from .models import Card


class CardLoadResults:
	def __init__(self):
		self.total = 0
		self.existing = 0
		self.created = 0


class CardXMLLoader:
	def load(self):
		result = CardLoadResults()
		db, _ = cardxml.load()
		result.total = len(db)

		for card in db.values():
			obj, created = Card.objects.get_or_create_from_cardxml(card)

			if created:
				result.created += 1
			else:
				result.existing += 1

		return result
