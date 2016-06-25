from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from .models import AuthToken


class RequireAuthToken(BasePermission):
	def has_permission(self, request, view):
		if request.user and request.user.is_staff:
			return True
		return hasattr(request, "auth_token")


class AuthTokenAuthentication(TokenAuthentication):
	model = AuthToken

	def authenticate(self, request):
		user_token_tuple = super(AuthTokenAuthentication, self).authenticate(request)
		if user_token_tuple is not None:
			request.auth_token = user_token_tuple[1]
		return user_token_tuple

	def authenticate_credentials(self, key):
		model = self.get_model()
		try:
			token = model.objects.get(key=key)
		except (model.DoesNotExist, ValueError):
			raise AuthenticationFailed("Invalid token.")

		if token.user:
			if not token.user.is_active:
				raise AuthenticationFailed("User cannot log in.")

		return token.user, token
