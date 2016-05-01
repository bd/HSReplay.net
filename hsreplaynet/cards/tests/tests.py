from django.test import TestCase
import json, random
from cards.models import *


class CardTests(TestCase):
	fixtures = ['cards_filtered.json', ]

	def test_card_manager_provides_random_cards(self):
		two_cost_card = Card.objects.random(cost=2)
		self.assertIsInstance(two_cost_card, Card)
		self.assertEqual(two_cost_card.cost, 2)

		random_card = Card.objects.random()
		self.assertIsInstance(random_card, Card)

		random_class_card = Card.objects.random(for_player_class_id=5)

		is_neutral = random_class_card.player_class == None
		if not is_neutral: # It's neutral
			is_class_five = random_class_card.player_class.id == 5
			if not is_class_five:
				self.fail("We did not get a random card that was either neutral or in class 5 (Paladin)")


class DeckTests(TestCase):
	fixtures = ['cards_filtered.json', ]

	def setUp(self):
		self.random_deck = Deck.objects.create()
		self.deck_size = 10
		self.cards_in_deck = []

		for i in range(self.deck_size):
			unique_card_added = False
			while not unique_card_added:
				random_card = Card.objects.random(cost=random.randint(1,10))
				if random_card not in self.cards_in_deck:
					unique_card_added = True
					self.cards_in_deck.append(random_card)
					Include.objects.create(deck = self.random_deck, card=random_card)

	def test_deck_knows_its_size(self):
		self.assertEqual(self.random_deck.size(), self.deck_size)

	def test_deck_provides_cards_of(self):
		two_cost_cards = self.random_deck.cards_of(cost=2)
		self.assertEqual(len(two_cost_cards), sum(1 for c in self.cards_in_deck if c.cost == 2))


class DeckManagerTests(TestCase):
	fixtures = ['cards_filtered.json', ]

	def test_random_deck_list_of_size(self):
		size = 30
		random_deck = Deck.objects.random_deck_list_of_size(size)
		self.assertEqual(len(random_deck), size)


class ModelsTest(TestCase):

	def test_create_beast_minion_with_deathrattle(self):
		savannah_highmane_str = """{"artist": "Milivoj Ceran", "cardId": "EX1_534", "cardSet": "Classic", "cost": 6, "collectible": true, "race": "Beast", "imgGold": "http://wow.zamimg.com/images/hearthstone/cards/enus/animated/EX1_534_premium.gif", "img": "http://wow.zamimg.com/images/hearthstone/cards/enus/original/EX1_534.png", "playerClass": "Hunter", "name": "Savannah Highmane", "inPlayText": "Master", "text": "<b>Deathrattle:</b> Summon two 2/2 Hyenas.", "mechanics": [{"name": "Deathrattle"}], "rarity": "Rare", "health": 5, "type": "Minion", "locale": "enUS", "flavor": "In the jungle, the mighty jungle, the lion gets slowly consumed by hyenas.", "attack": 6}"""
		savannah_highmane_json = json.loads(savannah_highmane_str)
		savannah_highmane, created = Card.objects.get_or_create_from_json(savannah_highmane_json)
		self.assertEqual(savannah_highmane.name, 'Savannah Highmane')
		self.assertEqual(savannah_highmane.attack, 6)
		self.assertEqual(savannah_highmane.race.name, "Beast")

		deathrattle = Mechanic.objects.get(name = "Deathrattle")
		first_mechanic = list(savannah_highmane.mechanics.all())[0]
		self.assertEqual(deathrattle, first_mechanic)

	def test_create_class_spell(self):
		velens_chosen_str = """{"artist": "Alex Horley Orlandelli", "cardId": "GVG_010", "cardSet": "Goblins vs Gnomes", "cost": 3, "collectible": true, "imgGold": "http://wow.zamimg.com/images/hearthstone/cards/enus/animated/GVG_010_premium.gif", "img": "http://wow.zamimg.com/images/hearthstone/cards/enus/original/GVG_010.png", "playerClass": "Priest", "name": "Velen's Chosen", "text": "Give a minion +2/+4 and <b>Spell Damage +1</b>.", "rarity": "Common", "type": "Spell", "locale": "enUS", "flavor": "Velen wrote a 'Lovely Card' for Tyrande with a picture of the Deeprun Tram that said 'I Choo-Choo-Choose you!'"}"""
		velens_chosen_json = json.loads(velens_chosen_str)
		velens_chosen, created = Card.objects.get_or_create_from_json(velens_chosen_json)
		spell_type = Type.objects.get(name = 'Spell')

		self.assertEqual(velens_chosen.name, "Velen's Chosen")
		self.assertEqual(velens_chosen.type, spell_type)

	def test_create_multi_mechanic_legendary_card(self):
		al_akir_str = """{"artist": "Raymond Swanland", "cardId": "NEW1_010", "elite": true, "cardSet": "Classic", "cost": 8, "collectible": true, "mechanics": [{"name": "Charge"}, {"name": "Divine Shield"}, {"name": "Windfury"}, {"name": "Taunt"}], "imgGold": "http://wow.zamimg.com/images/hearthstone/cards/enus/animated/NEW1_010_premium.gif", "img": "http://wow.zamimg.com/images/hearthstone/cards/enus/original/NEW1_010.png", "playerClass": "Shaman", "name": "Al'Akir the Windlord", "text": "<b>Windfury, Charge, Divine Shield, Taunt</b>", "rarity": "Legendary", "health": 5, "type": "Minion", "locale": "enUS", "flavor": "He is the weakest of the four Elemental Lords.  And the other three don't let him forget it.", "attack": 3}"""
		al_akir_json = json.loads(al_akir_str)
		al_akir, created = Card.objects.get_or_create_from_json(al_akir_json)

		self.assertEqual(al_akir.name, "Al'Akir the Windlord")
		self.assertEqual(len(al_akir.mechanics.all()), 4)

		shaman_player_class = PlayerClass.objects.get(name="Shaman")
		self.assertEqual(al_akir.player_class, shaman_player_class)
