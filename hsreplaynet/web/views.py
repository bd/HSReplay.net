from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import View
from hsreplaynet.web.models import GameReplayUpload


class MyReplaysView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request):
		replays = []

		for token in request.user.auth_tokens.all():
			replays.extend(list(GameReplayUpload.objects.filter(upload_token=token).all()))

		sorted_replays = sorted(replays, key=lambda r: r.global_game.match_start_timestamp, reverse=True)

		context = {"replays": sorted_replays, "count": len(sorted_replays)}
		return render(request, "games/my_replays.html", context)


class ReplayDetailView(View):
	def get(self, request, id):
		replay = get_object_or_404(GameReplayUpload, id=id)
		return render(request, "games/replay_detail.html", {"replay": replay})
