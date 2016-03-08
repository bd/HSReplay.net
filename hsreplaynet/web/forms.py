from django import forms

from .models import UploadAgentAPIKey


class UploadAgentAPIKeyForm(forms.ModelForm):
    class Meta:
        model = UploadAgentAPIKey
        fields = '__all__'