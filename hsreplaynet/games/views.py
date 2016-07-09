from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from .models import GameReplay


class MyReplaysView(LoginRequiredMixin, View):
	def get(self, request):
		replays = GameReplay.objects.filter(user=request.user)
		context = {"replays": replays}
		return render(request, "games/my_replays.html", context)


class ReplayDetailView(View):
	def get(self, request, id):
		replay = get_object_or_404(GameReplay, shortid=id)
		return render(request, "games/replay_detail.html", {"replay": replay})
