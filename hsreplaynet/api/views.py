from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet
from .models import AuthToken, UploadAgentAPIKey
from .serializers import AuthTokenSerializer, UploadAgentSerializer


class WriteOnlyOnceViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
	pass


class AuthTokenViewSet(WriteOnlyOnceViewSet):
	permission_classes = (AllowAny, )
	queryset = AuthToken.objects.all()
	serializer_class = AuthTokenSerializer


class UploadAgentViewSet(WriteOnlyOnceViewSet):
	queryset = UploadAgentAPIKey.objects.all()
	serializer_class = UploadAgentSerializer
