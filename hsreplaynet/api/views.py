from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.status import HTTP_201_CREATED
from hsreplaynet.accounts.models import AccountClaim
from .authentication import AuthTokenAuthentication, RequireAuthToken
from .models import AuthToken, UploadAgentAPIKey
from .serializers import AccountClaimSerializer, AuthTokenSerializer, UploadAgentSerializer


class WriteOnlyOnceViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
	pass


class AuthTokenViewSet(WriteOnlyOnceViewSet):
	permission_classes = (AllowAny, )
	queryset = AuthToken.objects.all()
	serializer_class = AuthTokenSerializer


class UploadAgentViewSet(WriteOnlyOnceViewSet):
	queryset = UploadAgentAPIKey.objects.all()
	serializer_class = UploadAgentSerializer


class CreateAccountClaimView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	queryset = AccountClaim.objects.all()
	serializer_class = AccountClaimSerializer

	def create(self, request):
		claim, _ = AccountClaim.objects.get_or_create(token_id=request.session["auth_token"])
		serializer = self.get_serializer(claim)
		headers = self.get_success_headers(serializer.data)
		response = Response(serializer.data, status=HTTP_201_CREATED, headers=headers)
		return response
