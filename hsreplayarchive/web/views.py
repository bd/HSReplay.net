from django.shortcuts import render_to_response
from django.views.generic import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


def home(request):
	return render_to_response('web/home.html')


class ReplayUploadView(View):

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super(ReplayUploadView, self).dispatch(*args, **kwargs)

	def post(self, request):
		response = HttpResponse()
		response.status_code = 200
		return response