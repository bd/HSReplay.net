from rest_framework import viewsets
from .models import AuthToken
from .serializers import UploadTokenSerializer


class UploadTokenViewSet(viewsets.ModelViewSet):
	queryset = AuthToken.objects.all()
	serializer_class = UploadTokenSerializer
