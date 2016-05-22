from rest_framework import serializers
from .models import AuthToken


class UploadTokenSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = AuthToken
		fields = ("key", )
