import random
from django.test import TestCase
from hearthstone import cardxml, enums
from hsreplaynet.cards.models import Card, Deck, Include
from hsreplaynet.test.base import CardDataBaseTest


class DeckTests(CardDataBaseTest):
	def setUp(self):
		self.random_deck = Deck.objects.create()
		self.deck_size = 10
		self.cards_in_deck = []

		for i in range(self.deck_size):
			unique_card_added = False
			while not unique_card_added:
				random_card = Card.objects.random(cost=random.randint(1, 10))
				if random_card not in self.cards_in_deck:
					unique_card_added = True
					self.cards_in_deck.append(random_card)
					Include.objects.create(deck=self.random_deck, card=random_card)

	def test_get_or_create_from_id_list(self):
		thirty_card_deck = [
			"AT_004", "AT_004", "AT_006", "AT_006", "AT_019",
			"CS2_142", "CS2_142", "CS2_146", "CS2_146", "CS2_161",
			"CS2_161", "CS2_169", "CS2_169", "CS2_181", "CS2_181",
			"CS2_189", "CS2_189", "CS2_200", "CS2_200", "AT_130",
			"GVG_081", "CS2_213", "EX1_371", "GVG_002", "NEW1_026",
			"EX1_405", "CS2_213", "EX1_250", "CS2_222", "AT_130"
		]

		d1, created1 = Deck.objects.get_or_create_from_id_list(thirty_card_deck)
		self.assertEqual(d1.size(), 30)
		self.assertTrue(created1)

		d2, created2 = Deck.objects.get_or_create_from_id_list(thirty_card_deck)
		self.assertEqual(d2.size(), 30)
		self.assertFalse(created2)

	def test_random_deck_list_of_size(self):
		size = 30
		random_deck = Deck.objects.random_deck_list_of_size(size)
		self.assertEqual(len(random_deck), size)

	def test_deck_knows_its_size(self):
		self.assertEqual(self.random_deck.size(), self.deck_size)

	def test_deck_provides_cards_of(self):
		two_cost_cards = self.random_deck.cards_of(cost=2)
		self.assertEqual(len(two_cost_cards), sum(1 for c in self.cards_in_deck if c.cost == 2))

	def test_card_manager_provides_random_cards(self):
		two_cost_card = Card.objects.random(cost=2)
		self.assertIsInstance(two_cost_card, Card)
		self.assertEqual(two_cost_card.cost, 2)

		random_card = Card.objects.random()
		self.assertIsInstance(random_card, Card)

		c = Card.objects.random(card_class=enums.CardClass.PALADIN)
		if c.card_class not in (enums.CardClass.NEUTRAL, enums.CardClass.PALADIN):
			self.fail("Expected card class to be NEUTRAL or PALADIN, got %r" % (c.card_class))


class ModelsTest(TestCase):
	def setUp(self):
		self.carddb, _ = cardxml.load()

	def test_al_akir(self):
		id = "NEW1_010"
		card = self.carddb[id]
		obj, created = Card.objects.get_or_create_from_cardxml(card)

		self.assertEqual(obj.id, id)
		self.assertEqual(obj.name, "Al'Akir the Windlord")
		self.assertEqual(obj.divine_shield, True)
		self.assertEqual(obj.taunt, True)
		self.assertEqual(obj.windfury, 1)
		self.assertEqual(obj.card_class, enums.CardClass.SHAMAN)

	def test_savannah_highmane(self):
		id = "EX1_534"
		card = self.carddb[id]
		obj, created = Card.objects.get_or_create_from_cardxml(card)

		self.assertEqual(obj.id, id)
		self.assertEqual(obj.name, "Savannah Highmane")
		self.assertEqual(obj.deathrattle, True)
		self.assertEqual(obj.atk, 6)
		self.assertEqual(obj.health, 5)
		self.assertEqual(obj.race, enums.Race.BEAST)
		self.assertEqual(obj.card_class, enums.CardClass.HUNTER)

	def test_velens_chosen(self):
		id = "GVG_010"
		card = self.carddb[id]
		obj, created = Card.objects.get_or_create_from_cardxml(card)

		self.assertEqual(obj.id, id)
		self.assertEqual(obj.name, "Velen's Chosen")
		self.assertEqual(obj.type, enums.CardType.SPELL)
		self.assertEqual(obj.card_class, enums.CardClass.PRIEST)
