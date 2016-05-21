from rest_framework import serializers
from hsreplaynet.web.models import SingleSiteUploadToken


class UploadTokenSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = SingleSiteUploadToken
		fields = ("token", )
