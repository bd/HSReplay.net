from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import View
from .models import GameReplay


class MyReplaysView(View):
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get(self, request):
		replays = GameReplay.objects.filter(user=request.user)
		context = {"replays": replays}
		return render(request, "games/my_replays.html", context)


class ReplayDetailView(View):
	def get(self, request, id):
		replay = get_object_or_404(GameReplay, id=id)
		return render(request, "games/replay_detail.html", {"replay": replay})
