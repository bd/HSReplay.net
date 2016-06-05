from rest_framework.authentication import SessionAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.status import HTTP_201_CREATED
from hsreplaynet.accounts.models import AccountClaim
from hsreplaynet.uploads.models import GameUpload
from . import serializers
from .authentication import AuthTokenAuthentication, RequireAuthToken
from .models import AuthToken, UploadAgentAPIKey


class WriteOnlyOnceViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
	pass


class AuthTokenViewSet(WriteOnlyOnceViewSet):
	permission_classes = (AllowAny, )
	queryset = AuthToken.objects.all()
	serializer_class = serializers.AuthTokenSerializer


class UploadAgentViewSet(WriteOnlyOnceViewSet):
	permission_classes = (AllowAny, )
	queryset = UploadAgentAPIKey.objects.all()
	serializer_class = serializers.UploadAgentSerializer


class CreateAccountClaimView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	queryset = AccountClaim.objects.all()
	serializer_class = serializers.AccountClaimSerializer

	def create(self, request):
		claim, _ = AccountClaim.objects.get_or_create(token_id=request.session["auth_token"])
		serializer = self.get_serializer(claim)
		headers = self.get_success_headers(serializer.data)
		response = Response(serializer.data, status=HTTP_201_CREATED, headers=headers)
		return response


class GameUploadViewSet(WriteOnlyOnceViewSet):
	authentication_classes = (AuthTokenAuthentication, SessionAuthentication)
	permission_classes = (RequireAuthToken, )
	queryset = GameUpload.objects.all()
	serializer_class = serializers.GameUploadSerializer


class CreateStatsSnapshotView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	serializer_class = serializers.SnapshotStatsSerializer
