from rest_framework.viewsets import ModelViewSet
from .models import AuthToken, UploadAgentAPIKey
from .serializers import AuthTokenSerializer, UploadAgentSerializer


class AuthTokenViewSet(ModelViewSet):
	queryset = AuthToken.objects.all()
	serializer_class = AuthTokenSerializer


class UploadAgentViewSet(ModelViewSet):
	queryset = UploadAgentAPIKey.objects.all()
	serializer_class = UploadAgentSerializer
