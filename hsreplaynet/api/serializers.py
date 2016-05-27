from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from hsreplaynet.uploads.models import GameUpload
from hsreplaynet.utils import get_client_ip
from .models import AuthToken, UploadAgentAPIKey


class AccountClaimSerializer(serializers.Serializer):
	url = serializers.ReadOnlyField(source="get_absolute_url")


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


class GameSerializer(serializers.Serializer):
	url = serializers.ReadOnlyField(source="get_absolute_url")


class GameUploadSerializer(serializers.HyperlinkedModelSerializer):
	status = serializers.IntegerField(read_only=True)
	tainted = serializers.BooleanField(read_only=True)
	game = GameSerializer(read_only=True)

	class Meta:
		model = GameUpload
		fields = ("type", "metadata", "file", "status", "tainted", "game")

	def create(self, data):
		data["upload_ip"] = get_client_ip(self.context["request"])
		return super(GameUploadSerializer, self).create(data)
