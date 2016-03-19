from django.shortcuts import render
from django.views.generic import View
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from hsreplayparser.parser import HSReplayParser
from datetime import date
from .forms import UploadAgentAPIKeyForm
from .models import *
import json

API_KEY_HEADER = 'x-hsreplay-api-key'
UPLOAD_TOKEN_HEADER = 'x-hsreplay-upload-token'


def fetch_header(request, header):
	if header in request.META:
		return request.META[header]

	django_header = 'HTTP_' + header.upper().replace('-', '_')
	if django_header in request.META:
		return request.META[django_header]

	return ''


def home(request):
	return render(request, 'web/home.html')


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
	try:
		replay = HSReplaySingleGameFileUpload.objects.get(id=id)
		response.content = replay.data
		response['Content-Type'] = 'application/vnd.hearthsim-hsreplay+xml'
		response.status_code = 200
	except Exception as e:
		response.status_code = 500
	return response


class GenerateSingleSiteUploadTokenView(View):

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def post(self, request):
		response = HttpResponse()
		api_key_header = fetch_header(request, API_KEY_HEADER)

		if not api_key_header:
			# Reject for not having included an API token
			response.status_code = 401
			response.content = "Missing %s header" % API_KEY_HEADER
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

	def get(self, request, api_key, single_site_upload_token):
		response = HttpResponse()
		upload_agent = None
		token = None

		try:
			upload_agent = UploadAgentAPIKey.objects.get(api_key=api_key)
		except UploadAgentAPIKey.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid API Key." % api_key
			return response

		try:
			token = SingleSiteUploadToken.objects.get(requested_by_upload_agent=upload_agent, token=single_site_upload_token)
		except SingleSiteUploadToken.DoesNotExist:
			response.status_code = 403
			response.content = "%s is not a valid upload token or was not assigned to this api kiey." % single_site_upload_token
			return response

		if request.user.is_authenticated():
			token.user = request.user
			token.save()
			return render(request, 'web/token_attached.html', {'token': str(token.token)})
		else:
			request.session['api_key'] = api_key
			request.session['upload_token'] = single_site_upload_token
			request.session['token_attachment_requested'] = True
			return HttpResponseRedirect(reverse("battlenet_login"))


class ReplayUploadView(View):

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super(ReplayUploadView, self).dispatch(*args, **kwargs)

	def post(self, request):
		response = HttpResponse()

		api_key_header = fetch_header(request, API_KEY_HEADER)
		upload_token_header = fetch_header(request, UPLOAD_TOKEN_HEADER)

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
