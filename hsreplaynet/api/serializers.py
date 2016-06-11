import json
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from hsreplaynet.stats import models as stats_models
from hsreplaynet.uploads.models import UploadEvent
from hsreplaynet.utils import get_client_ip
from .models import AuthToken, APIKey


class DeckListField(serializers.ListField):
	child = serializers.CharField()


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
			api_key = APIKey.objects.get(api_key=data.pop("api_key"))
		except (APIKey.DoesNotExist, ValueError) as e:
			raise ValidationError(str(e))
		ret = super(AuthTokenSerializer, self).create(data)
		api_key.tokens.add(ret)
		return ret


class APIKeySerializer(serializers.HyperlinkedModelSerializer):
	api_key = serializers.CharField(read_only=True)

	class Meta:
		model = APIKey
		fields = ("full_name", "email", "website", "api_key")


class StatsMetaSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.StatsMeta


class PlayerStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.PlayerStats


class ArenaDraftStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.ArenaDraftStats


class BrawlSeasonStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.BrawlSeasonStats


class RankedSeasonStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.RankedSeasonStats


class SnapshotStatsSerializer(serializers.Serializer):
	meta = StatsMetaSerializer()
	player_stats = PlayerStatsSerializer()
	arena_draft_stats = ArenaDraftStatsSerializer(required=False)
	brawl_season_stats = BrawlSeasonStatsSerializer(required=False)
	ranked_season_stats = RankedSeasonStatsSerializer(required=False)


class GameSerializer(serializers.Serializer):
	url = serializers.ReadOnlyField(source="get_absolute_url")


class PlayerSerializer(serializers.Serializer):
	rank = serializers.IntegerField(required=False, min_value=0, max_value=25, write_only=True)
	legend_rank = serializers.IntegerField(default=0, min_value=1, write_only=True)
	stars = serializers.IntegerField(required=False, max_value=95, write_only=True)
	wins = serializers.IntegerField(required=False, write_only=True)
	losses = serializers.IntegerField(required=False, write_only=True)
	deck = DeckListField(required=False, write_only=True)
	cardback = serializers.IntegerField(default=0, min_value=1, write_only=True)


class UploadEventSerializer(serializers.Serializer):
	id = serializers.UUIDField(read_only=True)
	type = serializers.IntegerField()
	status = serializers.IntegerField(read_only=True)
	tainted = serializers.BooleanField(read_only=True)
	game = GameSerializer(read_only=True)
	stats = SnapshotStatsSerializer(required=False)

	file = serializers.FileField()
	game_type = serializers.IntegerField(default=0, write_only=True)
	hearthstone_build = serializers.IntegerField(write_only=True)
	match_start_timestamp = serializers.DateTimeField(write_only=True)
	friendly_player = serializers.IntegerField(required=False, min_value=1, max_value=2, write_only=True)

	queue_time = serializers.IntegerField(default=0, min_value=1, write_only=True)
	spectator_mode = serializers.BooleanField(default=False, write_only=True)
	reconnecting = serializers.BooleanField(default=False, write_only=True)
	server_ip = serializers.IPAddressField(required=False, write_only=True)
	server_port = serializers.IntegerField(default=0, min_value=1, max_value=65535, write_only=True)
	client_id = serializers.IntegerField(default=0, min_value=1, write_only=True)
	game_id = serializers.IntegerField(default=0, min_value=1, write_only=True)
	spectate_key = serializers.CharField(default="", write_only=True)

	scenario_id = serializers.IntegerField(default=0, min_value=0, write_only=True)

	player1 = PlayerSerializer(required=False, write_only=True)
	player2 = PlayerSerializer(required=False, write_only=True)

	def create(self, data):
		request = self.context["request"]

		ret = UploadEvent(
			file=data.pop("file"),
			token_id=request.session["auth_token"],
			type=data.pop("type"),
			upload_ip=get_client_ip(request),
		)
		ret.metadata = json.dumps(data, cls=DjangoJSONEncoder)
		ret.save()

		return ret
