import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import View
from .models import AuthToken, UploadAgentAPIKey


logger = logging.getLogger(__name__)


def fetch_header(request, header):
	if header in request.META:
		return request.META[header]

	django_header = "HTTP_" + header.upper().replace("-", "_")
	if django_header in request.META:
		return request.META[django_header]

	return ""


def fetch_replay(request, id):
	from hsreplaynet.web.models import GameReplayUpload

	logger.info("Replay data requested for UUID: %s" % id)
	response = HttpResponse()
	replay = get_object_or_404(GameReplayUpload, id=id)

	response["Content-Type"] = "application/vnd.hearthsim-hsreplay+xml"
	response.status_code = 200

	replay.replay_xml.open()
	response.content = replay.replay_xml.read()
	logger.info("Fetching replay view is complete.")
	return response


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
