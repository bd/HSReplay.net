from rest_framework import viewsets
from hsreplaynet.web.models import SingleSiteUploadToken
from .serializers import UploadTokenSerializer


class UploadTokenViewSet(viewsets.ModelViewSet):
	queryset = SingleSiteUploadToken.objects.all()
	serializer_class = UploadTokenSerializer
