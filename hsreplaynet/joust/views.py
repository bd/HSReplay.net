from django.shortcuts import render
from django.views.generic import View

from web.models import HSReplaySingleGameFileUpload


class JoustStartupView(View):

	def get(self, request):
		if request.user.is_authenticated() and request.user.is_staff:
			replays = HSReplaySingleGameFileUpload.objects.order_by('-match_date').all()
		else:
			replays = HSReplaySingleGameFileUpload.objects.order_by('-match_date').filter(is_public=True).all()

		context = {'replays': replays }
		return render(request, 'joust/public_replay_list.html', context)


class JoustPrivateCollectionView(View):

	def get(self, request):
		replays = []

		for token in request.user.tokens.all():
			replays.append(HSReplaySingleGameFileUpload.objects.filter(upload_token=token).all())

		sorted_replays = sorted(replays, key=lambda r: r.match_date )

		context = {'replays': sorted_replays, 'count': len(sorted_replays) }
		return render(request, 'joust/private_replay_collection.html', context)


class ReplayDetailView(View):

	def get(self, request, id):

		return render(request, 'joust/replay_detail.html', {'replay_data_url': '/api/v1/replay/%s' % id})