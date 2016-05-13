from django import forms
from .models import UploadAgentAPIKey


class UploadAgentAPIKeyForm(forms.ModelForm):
	class Meta:
		model = UploadAgentAPIKey
		fields = "__all__"


class RawLogUploadForm(forms.Form):
	log = forms.CharField(widget=forms.Textarea)
	# hearthstone_build = forms.CharField(max_length=100, required=False)
	replay = forms.CharField(widget=forms.Textarea, required=False)
