from django.shortcuts import render
from django.views.generic import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import HSReplaySingleGameFileUpload
from hsreplayparser.parser import HSReplayParser
from datetime import date
from .forms import UploadAgentAPIKeyForm


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


class ReplayUploadView(View):

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super(ReplayUploadView, self).dispatch(*args, **kwargs)

	def post(self, request):
		response = HttpResponse()

		data = request.body.decode("utf-8")
		try:
			parser = HSReplayParser()
			parser.parse_data(data, is_final=True)

			if len(parser.replay.games) != 1:
				# Raise an error
				pass

			game = parser.replay.games[0]

			upload = HSReplaySingleGameFileUpload.objects.create(data=request.body)

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
		except Exception as e:
			response.status_code = 500

		return response
