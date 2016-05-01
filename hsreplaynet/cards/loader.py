""" Provides the utilities for loading & updating the local DB representation of cards from http://hearthstoneapi.com/
"""
import json
from urllib.request import Request, urlopen
from cards.models import Card

class CardLoadResults:
	cards_returned_from_api = 0
	num_cards_already_in_db = 0
	num_new_cards_created = 0


class HearthstoneApiLoader:
	API_KEY = "J2ovUBD10PmshNMz54M0EFWqreL7p1vF7rkjsnvm85i5LD6lQg"

	def __init__(self):
		pass

	def fetch_card_data(self):
		request = Request("https://omgvamp-hearthstone-v1.p.mashape.com/cards", headers={
			"X-Mashape-Key": self.API_KEY
		})
		response = urlopen(request).read().decode('utf-8')
		all_sets = json.loads(response)
		return all_sets

	def load(self):
		result = CardLoadResults()

		try:
			all_sets = self.fetch_card_data()

			for collection, cards in all_sets.items():

				for card in cards:

					card, created = Card.objects.get_or_create_from_json(card)
					result.cards_returned_from_api += 1

					if created:
						result.num_new_cards_created += 1
					else:
						result.num_cards_already_in_db += 1

		except Exception as e:
			print(json.dumps(card))
			raise e

		return result
