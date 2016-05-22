from rest_framework import viewsets
from .models import AuthToken, UploadAgentAPIKey
from .serializers import AuthTokenSerializer, UploadAgentSerializer


class AuthTokenViewSet(viewsets.ModelViewSet):
	queryset = AuthToken.objects.all()
	serializer_class = AuthTokenSerializer


class UploadAgentViewSet(viewsets.ModelViewSet):
	queryset = UploadAgentAPIKey.objects.all()
	serializer_class = UploadAgentSerializer
