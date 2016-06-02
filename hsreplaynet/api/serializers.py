from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from hsreplaynet.stats import models as stats_models
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


class StatsMetaSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.StatsMeta


class PlayerStatsSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.PlayerStats


class ArenaDraftStatsSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.ArenaDraftStats


class BrawlSeasonStatsSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.BrawlSeasonStats


class RankedSeasonStatsSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.RankedSeasonStats


class SnapshotStatsSerializer(serializers.Serializer):
	meta = StatsMetaSerializer()
	player_stats = PlayerStatsSerializer()
	arena_draft_stats = ArenaDraftStatsSerializer()
	brawl_season_stats = BrawlSeasonStatsSerializer()
	ranked_season_stats = RankedSeasonStatsSerializer()


class GameSerializer(serializers.Serializer):
	url = serializers.ReadOnlyField(source="get_absolute_url")


class GameUploadSerializer(serializers.Serializer):
	status = serializers.IntegerField(read_only=True)
	tainted = serializers.BooleanField(read_only=True)
	game = GameSerializer(read_only=True)
	stats = SnapshotStatsSerializer(required=False)

	game_type = serializers.IntegerField()
	file = serializers.FileField()
	match_start_timestamp = serializers.DateTimeField()
	# hearthstone_build = serializers.IntegerField(min_value=3140, required=False)
	friendly_player = serializers.IntegerField(min_value=1, max_value=2)

	queue_time = serializers.IntegerField(default=0, min_value=1)
	spectator_mode = serializers.BooleanField(default=False)
	reconnecting = serializers.BooleanField(default=False)
	server_ip = serializers.IPAddressField(required=False)
	server_port = serializers.IntegerField(default=0, min_value=1, max_value=65535)
	client_id = serializers.IntegerField(default=0, min_value=1)
	game_id = serializers.IntegerField(default=0, min_value=1)

	scenario_id = serializers.IntegerField(default=0, min_value=0)
	# brawl_season = serializers.IntegerField(default=0, min_value=1)
	# ladder_season = serializers.IntegerField(default=0, min_value=1)

	player1_rank = serializers.IntegerField(required=False, min_value=0, max_value=25)
	player2_rank = serializers.IntegerField(required=False, min_value=0, max_value=25)
	player1_legend_rank = serializers.IntegerField(default=0, min_value=1)
	player2_legend_rank = serializers.IntegerField(default=0, min_value=1)
	player1_deck = serializers.CharField(required=False)
	player2_deck = serializers.CharField(required=False)
	player1_cardback = serializers.IntegerField(default=0, min_value=1)
	player2_cardback = serializers.IntegerField(default=0, min_value=1)

	def create(self, data):
		data["upload_ip"] = get_client_ip(self.context["request"])
		return super(GameUploadSerializer, self).create(data)
