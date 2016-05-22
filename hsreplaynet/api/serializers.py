from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import AuthToken, UploadAgentAPIKey


class UserSerializer(serializers.Serializer):
	id = serializers.IntegerField(read_only=True)
	email = serializers.EmailField()
	username = serializers.CharField(max_length=100)


class AuthTokenSerializer(serializers.HyperlinkedModelSerializer):
	key = serializers.CharField(read_only=True)
	user = UserSerializer(read_only=True)
	api_key = serializers.CharField(write_only=True)

	class Meta:
		model = AuthToken
		fields = ("key", "user", "api_key")

	def create(self, data):
		try:
			api_key = UploadAgentAPIKey.objects.get(api_key=data.pop("api_key"))
		except (UploadAgentAPIKey.DoesNotExist, ValueError) as e:
			raise ValidationError(str(e))
		ret = super(AuthTokenSerializer, self).create(data)
		api_key.tokens.add(ret)
		return ret


class UploadAgentSerializer(serializers.HyperlinkedModelSerializer):
	api_key = serializers.CharField(read_only=True)

	class Meta:
		model = UploadAgentAPIKey
		fields = ("full_name", "email", "website", "api_key")
