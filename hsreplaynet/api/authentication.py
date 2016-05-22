from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from .models import AuthToken


class RequireAuthToken(BasePermission):
	def has_permission(self, request, view):
		return bool(request.session.get("auth_token"))


class AuthTokenAuthentication(TokenAuthentication):
	model = AuthToken

	def authenticate(self, request):
		user_token_tuple = super(AuthTokenAuthentication, self).authenticate(request)
		if user_token_tuple is not None:
			request.session["auth_token"] = user_token_tuple[1].key
		return user_token_tuple

	def authenticate_credentials(self, key):
		model = self.get_model()
		try:
			token = model.objects.get(key=key)
		except model.DoesNotExist:
			raise AuthenticationFailed("Invalid token.")

		if token.user:
			if not token.user.is_active:
				raise AuthenticationFailed("User cannot log in.")

		return token.user, token
