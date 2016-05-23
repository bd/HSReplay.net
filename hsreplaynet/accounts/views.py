from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import View
from .models import AccountClaim


class ClaimAccountView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, id):
		claim = get_object_or_404(AccountClaim, id=id)
		claim.token.user = request.user
		claim.token.save()
		claim.delete()
		msg = "You have claimed your account. Yay!"
		# XXX: using WARNING as a hack to ignore login/logout messages for now
		messages.add_message(request, messages.WARNING, msg)
		return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
