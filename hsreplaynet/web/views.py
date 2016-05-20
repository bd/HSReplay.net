import json
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from .forms import UploadAgentAPIKeyForm
from .models import *


logger = logging.getLogger(__name__)


def fetch_header(request, header):
	if header in request.META:
		return request.META[header]

	django_header = "HTTP_" + header.upper().replace("-", "_")
	if django_header in request.META:
		return request.META[django_header]

	return ""


class ContributeView(View):
	"""This view serves the API docs including the form to generate an API Token."""
	def get(self, request, method="client"):
		is_download_client = method != "api"
		context = {"is_download_client": is_download_client}
		if not is_download_client:
			context["form"] = UploadAgentAPIKeyForm()
		return render(request, "web/contribute.html", context)

	def post(self, request, method="api"):
		form = UploadAgentAPIKeyForm(request.POST)
		context = {"is_download_client": False}

		if form.is_valid():
			api_key = form.save()
			form = UploadAgentAPIKeyForm(instance=api_key)

		context["form"] = form

		return render(request, "web/contribute.html", {"form": form, "is_download_client": False})


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
			response.content = "Missing %s header" % settings.API_KEY_HEADER
			return response
		else:

			try:
				api_key = UploadAgentAPIKey.objects.get(api_key=api_key_header)
			except UploadAgentAPIKey.DoesNotExist:
				response.status_code = 403
				response.content = "%s is not a valid API Key." % api_key_header
				return response

			new_upload_token = SingleSiteUploadToken.objects.create(upload_agent=api_key)
			response.status_code = 201
			response.content = json.dumps({"single_site_upload_token": str(new_upload_token.token)})
			return response


class AttachSiteUploadTokenView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, api_key, single_site_upload_token):
		upload_token = single_site_upload_token
		token = None

		try:
			agent = UploadAgentAPIKey.objects.get(api_key=api_key)
		except UploadAgentAPIKey.DoesNotExist:
			return HttpResponseForbidden("Invalid API key: %r" % (api_key))

		try:
			token = SingleSiteUploadToken.objects.get(
				upload_agent=agent,
				token=upload_token
			)
		except SingleSiteUploadToken.DoesNotExist:
			return HttpResponseForbidden("Invalid upload token: %r" % (upload_token))

		token.user = request.user
		token.save()
		return render(request, "web/token_attached.html", {"token": str(token.token)})


class UploadTokenDetailsView(View):
	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, single_site_upload_token):
		response = HttpResponse()
		api_key_header = fetch_header(request, settings.API_KEY_HEADER)
		token = None

		try:
			agent = UploadAgentAPIKey.objects.get(api_key=api_key_header)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % api_key_header
			return response

		try:
			token = SingleSiteUploadToken.objects.get(upload_agent=agent, token=single_site_upload_token)
		except SingleSiteUploadToken.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid upload token or was not assigned to this api kiey." % single_site_upload_token
			return response

		response.status_code = 200
		response.content = json.dumps({
			"upload_token": str(token.token),
			"status": "ANONYMOUS" if not token.user else "REGISTERED",
			"battle_tag": token.user.username if token.user else "",
			"replays_are_public": token.replays_are_public
		})
		return response

	def put(self, request, single_site_upload_token):
		response = HttpResponse()
		api_key_header = fetch_header(request, settings.API_KEY_HEADER)

		try:
			agent = UploadAgentAPIKey.objects.get(api_key=api_key_header)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % api_key_header
			return response

		try:
			token = SingleSiteUploadToken.objects.get(upload_agent=agent, token=single_site_upload_token)
		except SingleSiteUploadToken.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid upload token or was not assigned to this api kiey." % single_site_upload_token
			return response

		body = json.loads(request.body.decode("utf-8"))
		if "replays_are_public" in body:
			token.replays_are_public = body["replays_are_public"]
			token.save()
			response.status_code = 200
			return response

		response.status_code = 400
		response.content = "You must include a JSON object with a 'replays_are_public' field when submitting a post request."
		return response
