from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from .models import UploadEvent


class UploadDetailView(View):
	def get(self, request, shortid):
		upload = get_object_or_404(UploadEvent, shortid=shortid)
		if upload.game:
			return HttpResponseRedirect(upload.game.get_absolute_url())

		return render(request, "uploads/processing.html", {"upload": upload})
