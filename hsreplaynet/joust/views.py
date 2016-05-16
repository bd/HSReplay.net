from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from web.models import *


class JoustPrivateCollectionView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request):
		replays = []

		for token in request.user.tokens.all():
			replays.extend(list(GameReplayUpload.objects.filter(upload_token=token).all()))

		sorted_replays = sorted(replays, key=lambda r: r.global_game.match_start_timestamp)

		context = {"replays": sorted_replays, "count": len(sorted_replays)}
		return render(request, "joust/my_replays.html", context)


class ReplayDetailView(View):
	def get(self, request, id):
		return render(request, "joust/replay_detail.html", {
			"replay_data_url": "/api/v1/replay/%s" % (id),
		})
