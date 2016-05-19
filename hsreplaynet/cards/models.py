import hashlib
import random
from datetime import datetime
from django.db import models
from hearthstone import enums


class CardManager(models.Manager):
	def random(self, cost=None, collectible=True, card_class=None):
		"""
		Return a random Card.

		Keyword arguments:
		cost: Restrict the set of candidate cards to cards of this mana cost.
		By default will be in the range 1 through 8 inclusive.
		collectible: Restrict the set of candidate cards to the set of collectible cards. (Default True)
		card_class: Restrict the set of candidate cards to this class.
		"""
		cost = random.randint(1, 8) if cost is None else cost
		cards = super(CardManager, self).filter(collectible=collectible)
		cards = cards.exclude(type=enums.CardType.HERO).filter(cost=cost)

		if card_class is not None:
			cards = [c for c in cards if c.card_class in (0, card_class)]

		if cards:
			return random.choice(cards)

	def get_or_create_from_cardxml(self, card):
		"""
		Returns a tuple with the object and a boolean to indicate
		whether it was created.
		"""
		qs = Card.objects.filter(id=card.id)
		if qs.exists():
			return qs.first(), False

		obj = Card(id=card.id)

		for k in dir(card):
			if k.startswith("_"):
				continue
			# Transfer all existing CardXML attributes to our model
			if hasattr(obj, k):
				setattr(obj, k, getattr(card, k))

		obj.save()
		return obj, True

		def get_valid_deck_list_card_set(self):
			if not hasattr(self, "_usable_cards"):
				card_list = card.objects.filter(collectible=True, type__not=CardType.HERO)
				self._usable_cards = set(c[0] for c in card_list.values_list("id"))

			return self._usable_cards


class Card(models.Model):
	id = models.CharField(primary_key=True, max_length=50)
	objects = CardManager()

	name = models.CharField(max_length=50)
	description = models.TextField(blank=True)
	flavortext = models.TextField(blank=True)
	how_to_earn = models.TextField(blank=True)
	how_to_earn_golden = models.TextField(blank=True)
	artist = models.CharField(max_length=255, blank=True)

	card_class = models.IntegerField(default=0)
	card_set = models.IntegerField(default=0)
	faction = models.IntegerField(default=0)
	race = models.IntegerField(default=0)
	rarity = models.IntegerField(default=0)
	type = models.IntegerField(default=0)

	collectible = models.BooleanField(default=False)
	battlecry = models.BooleanField(default=False)
	divine_shield = models.BooleanField(default=False)
	deathrattle = models.BooleanField(default=False)
	elite = models.BooleanField(default=False)
	evil_glow = models.BooleanField(default=False)
	inspire = models.BooleanField(default=False)
	forgetful = models.BooleanField(default=False)
	one_turn_effect = models.BooleanField(default=False)
	poisonous = models.BooleanField(default=False)
	ritual = models.BooleanField(default=False)
	secret = models.BooleanField(default=False)
	taunt = models.BooleanField(default=False)
	topdeck = models.BooleanField(default=False)

	atk = models.IntegerField(default=0)
	health = models.IntegerField(default=0)
	durability = models.IntegerField(default=0)
	cost = models.IntegerField(default=0)
	windfury = models.IntegerField(default=0)

	spare_part = models.BooleanField(default=False)
	overload = models.IntegerField(default=0)
	spell_damage = models.IntegerField(default=0)

	craftable = models.BooleanField(default=False)

	image = models.URLField(null=True, blank=True)
	image_gold = models.URLField(null=True, blank=True)

	class Meta:
		db_table = "card"

	def __str__(self):
		return self.name


class DeckManager(models.Manager):
	def random_deck_list_of_size(self, size):
		card_class = random.randint(2, 10)  # enums.CardClass
		result = []
		for i in range(size):
			candidate_card = Card.objects.random(card_class=card_class)
			if candidate_card:
				result.append(candidate_card.id)
		return result

	def get_or_create_from_id_list(self, id_list):
		digest = generate_digest_from_deck_list(id_list)
		existing_deck = Deck.objects.filter(digest=digest).first()
		if existing_deck:
			return (existing_deck, False)

		deck = Deck.objects.create(digest=digest)

		for card_id in id_list:
			include, created = deck.include_set.get_or_create(
				deck=deck,
				card_id=card_id,
				defaults={"count": 1}
			)

			if not created:
				# This must be an additional copy of a card we've
				# seen previously so we increment the count
				include.count += 1
				include.save()

		deck.save()
		return (deck, True)


def generate_digest_from_deck_list(id_list):
	sorted_cards = sorted(id_list)
	m = hashlib.md5()
	m.update(",".join(sorted_cards).encode("utf-8"))
	return m.hexdigest()


class Deck(models.Model):
	"""
	Represents an abstract collection of cards.

	The default sorting for cards when iterating over a deck is by
	mana cost and then alphabetical within cards of equal cost.
	"""
	id = models.AutoField(primary_key=True)
	objects = DeckManager()
	cards = models.ManyToManyField(Card, through="Include")
	digest = models.CharField(max_length=32, unique=True)
	created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

	def __str__(self):
		return "[" + ",".join(map(str, self.include_set.all())) + "]"

	def __repr__(self):
		return str(self)

	def __iter__(self):
		#sorted() is stable, so sort alphabetically first and then by mana cost
		alpha_sorted = sorted(self.cards.all(), key = lambda c: c.name)
		mana_sorted = sorted(alpha_sorted, key = lambda c: c.cost)
		return mana_sorted.__iter__()

	def save(self, *args, **kwargs):
		EMPTY_DECK_DIGEST = 'd41d8cd98f00b204e9800998ecf8427e'
		if self.digest != EMPTY_DECK_DIGEST and self.include_set.count() == 0:
			# A client has set a digest by hand, so don't recalculate it.
			return super(Deck, self).save(*args, **kwargs)
		else:
			self.digest = generate_digest_from_deck_list(self.card_id_list())
			return super(Deck, self).save(*args, **kwargs)

	def card_id_list(self):
		result = []

		for i in self.include_set.all():
			for n in range(0, i.count):
				result.append(i.card.id)

		return result

	def size(self):
		"""
		The number of cards in the deck.
		"""
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
