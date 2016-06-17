from rest_framework import permissions
from .models import APIKey


class APIKeyPermission(permissions.BasePermission):
	"""
	Permission check for presence of an API Key header
	http://www.django-rest-framework.org/api-guide/permissions/
	"""

	HEADER_NAME = "X-Api-Key"

	def has_permission(self, request, view):
		header = "HTTP_" + self.HEADER_NAME.replace("-", "_").upper()
		key = request.META.get(header, "")
		if not key:
			return False

		try:
			api_key = APIKey.objects.get(api_key=key)
		except APIKey.DoesNotExist:
			return False

		request.api_key = api_key
		return api_key.enabled
