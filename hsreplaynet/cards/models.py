from django.db import models
from random import randint
from datetime import datetime
from hearthstone import enums

class Faction(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'faction'


class PlayerClassManager(models.Manager):

	def random_player_class_name(self):
		return self.model.objects.get(id = randint(1,9)).name

	def suggest_player_class_for_deck(self, deck):
		player_class_count = { p: list(map(lambda c: c.player_class, deck.cards.all())).count(p) for p in PlayerClass.objects.all()}
		most_common_class = max(player_class_count.items(), key = lambda i: i[1])[0]
		return most_common_class


class PlayerClass(models.Model):
	id = models.AutoField(primary_key=True)
	objects = PlayerClassManager()
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'player_class'

class Type(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'type'


class Race(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'race'


class Collection(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'collection'


class Rarity(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'rarity'


class Mechanic(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	class Meta:
		db_table = 'mechanic'


class CardManager(models.Manager):

	def random(self, cost = None, collectible=True, for_player_class_id=None):
		"""Return a random Card.

		Keyword arguments:
		cost -- Restrict the set of candidate cards to cards of this mana cost. By default will be in the range 1 through 8 inclusive.
		collectible -- Restrict the set of candidate cards to the set of collectible cards. (Default True)
		for_player_class_id -- Restrict the set of candidate cards to this player class.
		"""
		cost = randint(1, 8) if not cost else cost
		cards_of_cost = super(CardManager, self).filter(collectible=collectible).exclude(type_id = 4).filter(cost=cost).all()

		if for_player_class_id:
			cards_of_cost = [c for c in cards_of_cost if c.player_class == None or c.player_class.id == for_player_class_id]

		if len(cards_of_cost) > 0:
			card_idx = randint(0, len(cards_of_cost) - 1)
			return cards_of_cost[card_idx]
		else:
			return None

	def get_valid_deck_list_card_set(self):
		if not hasattr(self, '_valid_deck_list_card_set'):
			inner_qs = Type.objects.filter(name__in=['Spell', 'Minion', 'Weapon']).values_list('id')
			card_list = set(c[0] for c in Card.objects.filter(collectible=True).filter(type__in=inner_qs).values_list('id'))
			self._valid_deck_list_card_set = card_list

		return self._valid_deck_list_card_set



	def get_or_create_from_json(self, json):
		""" Returns a tuple with the object followed by a boolean to indicate whether the object was created."""
		card_query = Card.objects.filter(id = json['cardId'])
		if card_query.exists():
			return (card_query.first(), False)

		card = Card(
			id = json['cardId'],
			name = json['name'],
			cost = json.get('cost', None),
			attack = json.get('attack', None),
			health = json.get('health', None),
			durability = json.get('durability', None),
			text = json.get('text', None),
			flavor = json.get('flavor', None),
			artist = json.get('artist', None),
			inPlayText = json.get('inPlayText', None),
			howToGet = json.get('howToGet', None),
			howToGetGold = json.get('howToGetGold', None),
			collectible = json.get('collectible', False),
			elite = json.get('elite', False),

		)

		if 'faction' in json:
			enum_id = int(enums.Faction[json['faction'].upper()])
			result = Faction.objects.get_or_create(name=json['faction'], defaults={'id': enum_id })
			card.faction = result[0]

		if 'rarity' in json:
			enum_id = int(enums.Rarity[json['rarity'].upper()])
			result = Rarity.objects.get_or_create(name=json['rarity'], defaults={'id': enum_id })
			card.rarity = result[0]

		if 'collection' in json:
			result = Collection.objects.get_or_create(name=json['collection'])
			card.collection = result[0]

		if 'race' in json:
			enum_name = 'MECHANICAL' if json['race'].upper() == 'MECH' else json['race'].upper()
			enum_id = int(enums.Race[enum_name])
			result = Race.objects.get_or_create(name = json['race'], defaults={'id': enum_id })
			card.race = result[0]

		if 'type' in json:
			enum_id = int(enums.CardType[json['type'].upper().replace(' ', '_')])
			result = Type.objects.get_or_create(name=json['type'], defaults={'id': enum_id })
			card.type = result[0]

		if 'playerClass' in json:
			enum_id = int(enums.CardClass[json['playerClass'].upper()])
			result = PlayerClass.objects.get_or_create(name=json['playerClass'], defaults={'id': enum_id })
			card.player_class = result[0]

		if 'img' in json:
			card.img = json['img']

		if 'imgGold' in json:
			card.imgGold = json['imgGold']

		card.save()

		if 'mechanics' in json:
			for mechanic in json['mechanics']:
				result = Mechanic.objects.get_or_create(name=mechanic['name'])
				card.mechanics.add(result[0])

		return (card, True)


class Card(models.Model):
	id = models.CharField(primary_key=True, max_length=50)
	objects = CardManager()
	name = models.CharField(max_length=50)
	cost = models.IntegerField(null=True, blank=True)
	attack = models.IntegerField(null=True, blank=True)
	health = models.IntegerField(null=True, blank=True)
	durability = models.IntegerField(null=True, blank=True)
	faction = models.ForeignKey(Faction, null=True, blank=True, on_delete=models.SET_NULL)
	text = models.TextField(null=True, blank=True)
	flavor = models.TextField(null=True, blank=True)
	artist = models.CharField(max_length=255, null=True, blank=True)
	inPlayText = models.TextField(null=True, blank=True)
	howToGet = models.TextField(null=True, blank=True)
	howToGetGold = models.TextField(null=True, blank=True)
	collectible = models.BooleanField(default=False)
	elite = models.BooleanField(default=False)
	mechanics = models.ManyToManyField(Mechanic, db_table='card_mechanic')
	rarity = models.ForeignKey(Rarity, null=True, blank=True)
	collection = models.ForeignKey(Collection, null=True, blank=True)
	race = models.ForeignKey(Race, null=True, blank=True, on_delete=models.SET_NULL)
	type = models.ForeignKey(Type)
	player_class = models.ForeignKey(PlayerClass, null=True, blank=True, on_delete=models.SET_NULL)
	img = models.URLField(null=True, blank=True)
	imgGold = models.URLField(null=True, blank=True)

	class Meta:
		db_table = 'card'

	def __str__(self):
		return self.name


class DeckManager(models.Manager):

	def random_deck_list_of_size(self, size):
		player_class = randint(2, 10) # Values from hearthstone.enums.CardClass
		return [Card.objects.random(for_player_class_id= player_class).id for i in range(size)]

	def create_from_id_list(self, card_id_list):
		deck = Deck.objects.create()

		for card_id in card_id_list:
			include, created = deck.include_set.get_or_create(deck = deck, card_id = card_id, defaults={'count': 1 })
			if not created:
				# This must be an additional copy of a card we've seen previously so we increment the count
				include.count += 1
				include.save()

		deck.player_class = PlayerClass.objects.suggest_player_class_for_deck(deck)
		deck.save()

		return deck


class Deck(models.Model):
	""" Represents an abstract collection of cards.

	The default sorting for cards when iterating over a deck is by mana cost and then alphabetical within cards of
	equal cost.

	"""

	id = models.AutoField(primary_key=True)
	objects = DeckManager()
	cards = models.ManyToManyField(Card, through='Include')

	created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	modified = models.DateTimeField(auto_now=True, null=True, blank=True)

	def __str__(self):
		return "[" + ",".join(map(str, self.include_set.all())) + "]"

	def __repr__(self):
		return str(self)

	def __iter__(self):
		#sorted() is stable, so sort alphabetically first and then by mana cost
		alpha_sorted = sorted(self.cards.all(), key = lambda c: c.name)
		mana_sorted = sorted(alpha_sorted, key = lambda c: c.cost)
		return mana_sorted.__iter__()

	def card_id_list(self):
		result = []

		for i in self.include_set.all():
			for n in range(0, i.count):
				result.append(i.card.id)

		return result

	def size(self):
		""" The number of cards in the deck. """
		return sum(i.count for i in self.include_set.all())

	def cards_of(self, cost = None, attack = None, health = None):
		result = self.cards

		if cost:
			result = result.filter(cost = cost)

		if attack:
			result = result.filter(attack = attack)

		if health:
			result = result.filter(health = health)

		return result.all()


class Include(models.Model):
	id = models.AutoField(primary_key=True)
	deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
	card = models.ForeignKey(Card, on_delete=models.PROTECT)
	count = models.IntegerField(default=1)

	def __str__(self):
		return "%s x %s" % (self.card.name, self.count)

	class Meta:
		unique_together = ("deck", "card")


class CardCollectionAuditLog(models.Model):
	id = models.AutoField(primary_key=True)
	job_date = models.DateField()

	# Load Cards
	card_collection_start = models.DateTimeField()
	card_collection_end = models.DateTimeField(null=True, blank=True)
	num_new_cards_loaded = models.IntegerField(default=0)
	card_collection_succeeded = models.BooleanField(default=False)
	exception_text = models.TextField()