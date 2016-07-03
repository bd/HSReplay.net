from rest_framework.authentication import SessionAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.status import HTTP_201_CREATED
from hsreplaynet.accounts.models import AccountClaim
from hsreplaynet.games.models import GameReplay
from hsreplaynet.uploads.models import UploadEvent
from . import serializers
from .authentication import AuthTokenAuthentication, RequireAuthToken
from .models import AuthToken, APIKey
from .permissions import APIKeyPermission


class WriteOnlyOnceViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
	pass


class AuthTokenViewSet(WriteOnlyOnceViewSet):
	permission_classes = (APIKeyPermission, )
	queryset = AuthToken.objects.all()
	serializer_class = serializers.AuthTokenSerializer


class APIKeyViewSet(WriteOnlyOnceViewSet):
	permission_classes = (AllowAny, )
	queryset = APIKey.objects.all()
	serializer_class = serializers.APIKeySerializer


class CreateAccountClaimView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	queryset = AccountClaim.objects.all()
	serializer_class = serializers.AccountClaimSerializer

	def create(self, request):
		claim, _ = AccountClaim.objects.get_or_create(token=request.auth_token)
		serializer = self.get_serializer(claim)
		headers = self.get_success_headers(serializer.data)
		response = Response(serializer.data, status=HTTP_201_CREATED, headers=headers)
		return response


class UploadEventViewSet(WriteOnlyOnceViewSet):
	authentication_classes = (AuthTokenAuthentication, SessionAuthentication)
	permission_classes = (RequireAuthToken, APIKeyPermission)
	queryset = UploadEvent.objects.all()
	serializer_class = serializers.UploadEventSerializer


class GameReplayViewSet(RetrieveModelMixin, GenericViewSet):
	queryset = GameReplay.objects.all()
	serializer_class = serializers.GameReplaySerializer
	lookup_field = "shortid"


class CreateStatsSnapshotView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	serializer_class = serializers.SnapshotStatsSerializer
