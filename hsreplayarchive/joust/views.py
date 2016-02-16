from django.shortcuts import render
from django.views.generic import View


class JoustStartupView(View):

	def get(self, request):
		return render(request, 'joust/joust_startup.html')


class ReplayDetailView(View):

	def get(self, request, id):

		return render(request, 'joust/replay_detail.html', {'replay_data_url': '/api/v1/replay/%s' % id})