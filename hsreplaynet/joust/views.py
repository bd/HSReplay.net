from django.shortcuts import render
from django.views.generic import View
from web.models import *


class JoustPrivateCollectionView(View):
	def get(self, request):
		replays = []

		for token in request.user.tokens.all():
			replays.extend(list(GameReplayUpload.objects.filter(upload_token=token).all()))

		sorted_replays = sorted(replays, key=lambda r: r.global_game.match_start_timestamp)

		context = {"replays": sorted_replays, "count": len(sorted_replays)}
		return render(request, "joust/private_replay_collection.html", context)


class ReplayDetailView(View):
	def get(self, request, id):
		return render(request, "joust/replay_detail.html", {
			"replay_data_url": "/api/v1/replay/%s" % (id),
		})
