from rest_framework import serializers
from .models import AuthToken, UploadAgentAPIKey


class AuthTokenSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = AuthToken
		fields = ("key", )


class UploadAgentSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = UploadAgentAPIKey
		fields = ("full_name", "email", "website", "api_key")

	api_key = serializers.CharField(read_only=True)
