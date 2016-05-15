import json
import os
import logging
from datetime import datetime
from io import StringIO
from zlib import decompress
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from hsreplay.dumper import parse_log, create_document, game_to_xml, __version__ as hsreplay_version
from hsreplay.utils import pretty_xml
from hsreplayparser.parser import HSReplayParser
from web.utils import fetch_s3_object
from .forms import UploadAgentAPIKeyForm, RawLogUploadForm
from .models import *


logger = logging.getLogger(__name__)


def fetch_header(request, header):
	if header in request.META:
		return request.META[header]

	django_header = 'HTTP_' + header.upper().replace('-', '_')
	if django_header in request.META:
		return request.META[django_header]

	return ''


def home(request):
	return render(request, 'web/home.html')


class UploadRawReplayView(View):

	def get(self, request):
		return render(request, 'web/upload_raw_log.html', {'form': RawLogUploadForm()})

	def post(self, request):
		form = RawLogUploadForm(request.POST)
		context = {}

		if form.is_valid():

			raw_log = form.cleaned_data['log']

			parser = parse_log(StringIO(raw_log), processor='GameState', date=datetime.now())

			doc = create_document(version=hsreplay_version, build=None)
			game = game_to_xml(parser.games[0], game_meta=None, player_meta=None, decks=None)
			doc.append(game)

			replay_xml = pretty_xml(doc)
			form = RawLogUploadForm({'log':raw_log, 'replay':replay_xml})

		# If we get here there are form errors to present.
		context['form'] = form

		return render(request, 'web/upload_raw_log.html', context)


class ContributeView(View):

	def get(self, request, method='client'):
		is_download_client = method != 'api'
		context = {'is_download_client': is_download_client}
		if not is_download_client:
			context['form'] = UploadAgentAPIKeyForm()
		return render(request, 'web/contribute.html', context)

	def post(self, request, method='api'):
		form = UploadAgentAPIKeyForm(request.POST)
		context = {'is_download_client': False}

		if form.is_valid():
			api_key = form.save()
			form = UploadAgentAPIKeyForm(instance = api_key)

		context['form'] = form

		return render(request, 'web/contribute.html', {'form': form, 'is_download_client': False})


def fetch_replay(request, id):
	response = HttpResponse()
	logger.info("Replay data requested for UUID: %s" % id)

	try:
		replay = HSReplaySingleGameFileUpload.objects.get(id=id)

		s3_replay_obj = None
		try:
			logger.info("Attempting to fetch replay using key: %s from bucket: %s" % (replay.get_s3_key(), settings.S3_REPLAY_STORAGE_BUCKET))
			s3_replay_obj = fetch_s3_object(settings.S3_REPLAY_STORAGE_BUCKET, replay.get_s3_key())

			if not s3_replay_obj:
				logger.info("S3 Object not found. Attempting to fetch using key: %s" % str(replay.id))
				# Fallback to fetch replays before we started using date prefixing
				s3_replay_obj = fetch_s3_object(settings.S3_REPLAY_STORAGE_BUCKET, str(replay.id))
				if not s3_replay_obj:
					logger.info("S3 Object still not found.")

		except Exception as e:
			logger.exception("Boto Connection To S3 Failed")

		if s3_replay_obj:
			logger.info("Successfully retrieved object from S3")
			if 'ContentEncoding' in s3_replay_obj and s3_replay_obj['ContentEncoding'] == 'gzip':
				logger.info("Replay object has been gzipped.")
				response.content = decompress(s3_replay_obj['Body'].read())
			else:
				logger.info("Replay object is not gzipped")
				response.content = s3_replay_obj['Body'].read()
		else:
			logger.info("Replay data served from DB")
			response.content = replay.data

		response['Content-Type'] = 'application/vnd.hearthsim-hsreplay+xml'
		response.status_code = 200

	except Exception as e:
		logger.exception("An unexpected error occurred fetching the replay")
		response.status_code = 500

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

			new_upload_token = SingleSiteUploadToken.objects.create(requested_by_upload_agent=api_key)
			response.status_code = 201
			response.content = json.dumps({"single_site_upload_token": str(new_upload_token.token)})
			return response


class AttachSiteUploadTokenView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request, api_key, single_site_upload_token):
		upload_token = single_site_upload_token
		response = HttpResponse()
		upload_agent = None
		token = None

		try:
			upload_agent = UploadAgentAPIKey.objects.get(api_key=api_key)
		except UploadAgentAPIKey.DoesNotExist:
			return HttpResponseForbidden("Invalid API key: %r" % (api_key))

		try:
			token = SingleSiteUploadToken.objects.get(
				requested_by_upload_agent=upload_agent,
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
		upload_agent = None
		token = None

		try:
			upload_agent = UploadAgentAPIKey.objects.get(api_key=api_key_header)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % api_key_header
			return response

		try:
			token = SingleSiteUploadToken.objects.get(requested_by_upload_agent=upload_agent, token=single_site_upload_token)
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
		upload_agent = None
		token = None

		try:
			upload_agent = UploadAgentAPIKey.objects.get(api_key=api_key_header)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % api_key_header
			return response

		try:
			token = SingleSiteUploadToken.objects.get(requested_by_upload_agent=upload_agent, token=single_site_upload_token)
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
		else:
			response.status_code = 400
			response.content = "You must include a JSON object with a 'replays_are_public' field when submitting a post request."
			return response


class ReplayUploadView(View):

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super(ReplayUploadView, self).dispatch(*args, **kwargs)

	def post(self, request):
		response = HttpResponse()

		api_key_header = fetch_header(request, settings.API_KEY_HEADER)
		upload_token_header = fetch_header(request, settings.UPLOAD_TOKEN_HEADER)

		upload_token = None
		if api_key_header and upload_token_header:
			upload_agent = UploadAgentAPIKey.objects.get(api_key=api_key_header)
			upload_token = SingleSiteUploadToken.objects.get(token=upload_token_header)
			if upload_token.requested_by_upload_agent != upload_agent:
				response.status_code = 403
				response.content = "The upload token: %s was not issued to the API key: %s" % (upload_token_header, api_key_header)

		data = request.body.decode("utf-8")
		try:
			parser = HSReplayParser()
			parser.parse_data(data, is_final=True)

			if len(parser.replay.games) != 1:
				# Raise an error
				pass

			game = parser.replay.games[0]

			upload = HSReplaySingleGameFileUpload.objects.create(data=request.body)

			if upload_token:
				upload.upload_token = upload_token
				upload.is_public = upload_token.replays_are_public

			if game.first_player.name:
				upload.player_1_name = game.first_player.name

			if game.second_player.name:
				upload.player_2_name = game.second_player.name

			if game.match_date:
				upload.match_date = game.match_date
			else:
				upload.match_date = date.today()

			upload.save()

			response['Location'] = '%s://%s/api/v1/replay/%s' % (request.scheme, request.get_host(), upload.id)
			response.status_code = 201
			response.content = json.dumps({"replay_uuid": str(upload.id)})
		except Exception as e:
			response.status_code = 500

		return response
