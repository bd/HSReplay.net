from django.shortcuts import render_to_response
from django.views.generic import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import HSReplayFile


def home(request):
	return render_to_response('web/home.html')


def fetch_replay(request, id):
	response = HttpResponse()
	try:
		replay = HSReplayFile.objects.get(id=id)
		response.content = replay.data
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
			replay = HSReplayFile.objects.create(data=request.body)
			replay.save()

			response['Location'] = '%s://%s/api/v1/replay/%s' % (request.scheme, request.get_host(), replay.id)
			response.status_code = 201
		except Exception as e:
			response.status_code = 500

		return response
