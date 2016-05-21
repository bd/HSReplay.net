from django.shortcuts import render
from django.views.generic import View
from .forms import UploadAgentAPIKeyForm


class APIDocsView(View):
	"""
	This view serves the legacy API docs including
	the form to generate an API Token.
	"""
	def get(self, request):
		context = {"form": UploadAgentAPIKeyForm()}
		return render(request, "api_docs.html", context)

	def post(self, request):
		form = UploadAgentAPIKeyForm(request.POST)

		if form.is_valid():
			api_key = form.save()
			form = UploadAgentAPIKeyForm(instance=api_key)

		return render(request, "api_docs.html", {"form": form})
