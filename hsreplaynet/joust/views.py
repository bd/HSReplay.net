from django.shortcuts import render
from django.views.generic import View

from web.models import HSReplaySingleGameFileUpload


class JoustStartupView(View):

	def get(self, request):
		context = {'replays': HSReplaySingleGameFileUpload.objects.order_by('-match_date').all() }
		return render(request, 'joust/replay_list.html', context)


class ReplayDetailView(View):

	def get(self, request, id):

		return render(request, 'joust/replay_detail.html', {'replay_data_url': '/api/v1/replay/%s' % id})