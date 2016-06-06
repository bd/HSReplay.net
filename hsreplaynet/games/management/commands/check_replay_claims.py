from django.core.management.base import BaseCommand
from hsreplaynet.api.models import AuthToken
from ...models import PendingReplayOwnership


class Command(BaseCommand):
	def handle(self, *args, **options):
		tokens = AuthToken.objects.exclude(user=None)
		for token in tokens:
			claims = PendingReplayOwnership.objects.filter(token=token)
			count = claims.count()
			if count:
				print("Found %r replays unclaimed by %r... fixing." % (count, token.user))
				for claim in claims:
					claims.replay.user = token.user
					claims.replay.save()
				claims.delete()

		print("%r tokens verified." % (tokens.count()))
