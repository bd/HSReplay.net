import json
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from .models import *


logger = logging.getLogger(__name__)


def fetch_header(request, header):
	if header in request.META:
		return request.META[header]

	django_header = "HTTP_" + header.upper().replace("-", "_")
	if django_header in request.META:
		return request.META[django_header]

	return ""


def fetch_replay(request, id):
	logger.info("Replay data requested for UUID: %s" % id)
	response = HttpResponse()
	replay = get_object_or_404(GameReplayUpload, id=id)

	response["Content-Type"] = "application/vnd.hearthsim-hsreplay+xml"
	response.status_code = 200

	replay.replay_xml.open()
	response.content = replay.replay_xml.read()
	logger.info("Fetching replay view is complete.")
	return response


class GenerateSingleSiteUploadTokenView(View):
	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def post(self, request):
		response = HttpResponse()
		api_key_header = fetch_header(request, settings.API_KEY_HEADER)

		if not api_key_header:
			# Reject for not having included an API token
			response.status_code = 401
			response.content = "Missing %s header" % (settings.API_KEY_HEADER)
			return response

		try:
			api_key = UploadAgentAPIKey.objects.get(api_key=api_key_header)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % (api_key_header)
			return response

		token = SingleSiteUploadToken.objects.create()
		api_key.tokens.add(token)
		response.status_code = 201
		response.content = json.dumps({"token": str(token.token)})
		return response


class AttachSiteUploadTokenView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, api_key, token):
		try:
			token = SingleSiteUploadToken.objects.get(token=token)
		except SingleSiteUploadToken.DoesNotExist:
			return HttpResponseForbidden("Invalid upload token: %r" % (token))

		try:
			agent = UploadAgentAPIKey.objects.get(api_key=api_key)
		except UploadAgentAPIKey.DoesNotExist:
			return HttpResponseForbidden("Invalid API key: %r" % (api_key))

		token.user = request.user
		token.save()
		context = {"token": token, "agent": agent}
		return render(request, "web/token_attached.html", context)


class UploadTokenDetailsView(View):
	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, token):
		response = HttpResponse()
		api_key_header = fetch_header(request, settings.API_KEY_HEADER)
		token = None

		try:
			UploadAgentAPIKey.objects.get(api_key=api_key_header)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % api_key_header
			return response

		try:
			token = SingleSiteUploadToken.objects.get(token=token)
		except SingleSiteUploadToken.DoesNotExist:
			response.status_code = 403
			response.content = "Invalid upload token: %r" % (token)
			return response

		response.status_code = 200
		response.content = json.dumps({
			"upload_token": str(token.token),
			"status": "ANONYMOUS" if not token.user else "REGISTERED",
			"battle_tag": token.user.username if token.user else "",
		})
		return response
