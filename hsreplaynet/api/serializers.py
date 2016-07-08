import json
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers
from hsreplaynet.games.models import GameReplay, GlobalGame, GlobalGamePlayer
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
	username = serializers.CharField(max_length=100)


class AuthTokenSerializer(serializers.HyperlinkedModelSerializer):
	key = serializers.UUIDField(read_only=True)
	user = UserSerializer(read_only=True)

	class Meta:
		model = AuthToken
		fields = ("key", "user")

	def create(self, data):
		ret = super(AuthTokenSerializer, self).create(data)
		api_key = self.context["request"].api_key
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
	legend_rank = serializers.IntegerField(required=False, min_value=1, write_only=True)
	stars = serializers.IntegerField(required=False, max_value=95, write_only=True)
	wins = serializers.IntegerField(required=False, write_only=True)
	losses = serializers.IntegerField(required=False, write_only=True)
	deck = DeckListField(required=False, write_only=True)
	cardback = serializers.IntegerField(required=False, min_value=1, write_only=True)


class UploadEventSerializer(serializers.Serializer):
	id = serializers.UUIDField(read_only=True)
	shortid = serializers.UUIDField(read_only=True)
	type = serializers.IntegerField()
	status = serializers.IntegerField(read_only=True)
	tainted = serializers.BooleanField(read_only=True)
	game = GameSerializer(read_only=True)
	stats = SnapshotStatsSerializer(required=False)

	file = serializers.FileField(write_only=True)
	game_type = serializers.IntegerField(default=0, write_only=True)
	build = serializers.IntegerField(write_only=True)
	match_start_timestamp = serializers.DateTimeField(write_only=True)
	friendly_player = serializers.IntegerField(required=False, min_value=1, max_value=2, write_only=True)

	queue_time = serializers.IntegerField(required=False, min_value=1, write_only=True)
	spectator_mode = serializers.BooleanField(default=False, write_only=True)
	reconnecting = serializers.BooleanField(default=False, write_only=True)
	server_ip = serializers.IPAddressField(required=False, write_only=True)
	server_port = serializers.IntegerField(required=False, min_value=1, max_value=65535, write_only=True)
	client_id = serializers.IntegerField(required=False, min_value=1, write_only=True)
	game_id = serializers.IntegerField(required=False, min_value=1, write_only=True)
	spectate_key = serializers.CharField(default="", write_only=True)

	scenario_id = serializers.IntegerField(required=False, min_value=0, write_only=True)

	player1 = PlayerSerializer(required=False, write_only=True)
	player2 = PlayerSerializer(required=False, write_only=True)

	def create(self, data):
		request = self.context["request"]

		ret = UploadEvent(
			file=data.pop("file"),
			token=request.auth_token,
			api_key=request.api_key,
			type=data.pop("type"),
			upload_ip=get_client_ip(request),
		)
		ret.metadata = json.dumps(data, cls=DjangoJSONEncoder)
		ret.save()

		return ret


class GlobalGamePlayerSerializer(serializers.ModelSerializer):
	class Meta:
		model = GlobalGamePlayer
		fields = (
			"name", "player_id", "account_hi", "account_lo", "is_ai", "is_first",
			"hero_id", "hero_premium", "final_state",
		)


class GlobalGameSerializer(serializers.ModelSerializer):
	players = GlobalGamePlayerSerializer(many=True, read_only=True)

	class Meta:
		model = GlobalGame
		fields = (
			"build", "match_start_timestamp", "match_end_timestamp",
			"game_type", "ladder_season", "scenario_id", "players"
		)


class GameReplaySerializer(serializers.ModelSerializer):
	user = UserSerializer(read_only=True)
	global_game = GlobalGameSerializer(read_only=True)

	class Meta:
		model = GameReplay
		fields = (
			"shortid", "user", "global_game", "is_spectated_game", "friendly_player_id",
			"replay_xml", "won", "disconnected", "reconnecting"
		)
		lookup_field = "shortid"
