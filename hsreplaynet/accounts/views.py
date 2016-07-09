from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.views.generic import View
from hsreplaynet.utils import get_uuid_object_or_404
from .models import AccountClaim


class ClaimAccountView(LoginRequiredMixin, View):
	def get(self, request, id):
		claim = get_uuid_object_or_404(AccountClaim, id=id)

		claim.token.user = request.user
		claim.token.save()

		# Claim all of the token's replays and delete the claim
		replay_claims = claim.token.replay_claims.all()
		for replay_claim in replay_claims:
			replay_claim.replay.user = request.user
			replay_claim.replay.save()
		replay_claims.delete()

		claim.delete()
		msg = "You have claimed your account. Yay!"
		# XXX: using WARNING as a hack to ignore login/logout messages for now
		messages.add_message(request, messages.WARNING, msg)
		return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
