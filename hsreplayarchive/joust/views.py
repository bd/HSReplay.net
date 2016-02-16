from django.shortcuts import render
from django.views.generic import View

from web.models import HSReplayFile

class JoustStartupView(View):

	def get(self, request):
		return render(request, 'joust/replay_list.html', {'replays': HSReplayFile.objects.all() })


class ReplayDetailView(View):

	def get(self, request, id):

		return render(request, 'joust/replay_detail.html', {'replay_data_url': '/api/v1/replay/%s' % id})