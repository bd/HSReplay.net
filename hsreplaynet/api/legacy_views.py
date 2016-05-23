import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from .models import AuthToken, UploadAgentAPIKey


logger = logging.getLogger(__name__)


class AttachSiteUploadTokenView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, api_key, token):
		try:
			token = AuthToken.objects.get(key=token)
		except AuthToken.DoesNotExist:
			return HttpResponseForbidden("Invalid upload token: %r" % (token))

		try:
			agent = UploadAgentAPIKey.objects.get(api_key=api_key)
		except UploadAgentAPIKey.DoesNotExist:
			return HttpResponseForbidden("Invalid API key: %r" % (api_key))

		token.user = request.user
		token.save()
		context = {"token": token, "agent": agent}
		return render(request, "web/token_attached.html", context)
