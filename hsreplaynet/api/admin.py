from django.contrib import admin
from hsreplaynet.utils import set_user
from .models import *


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
	actions = (set_user, )
	date_hierarchy = "created"
	list_display = ("__str__", "user", "created")
	raw_id_fields = ("user", )


class AuthTokenInline(admin.TabularInline):
	model = UploadAgentAPIKey.tokens.through
	raw_id_fields = ("authtoken", )
	extra = 3


@admin.register(UploadAgentAPIKey)
class UploadAgentAPIKeyAdmin(admin.ModelAdmin):
	list_display = ("__str__", "email", "website", "api_key", "enabled")
	search_fields = ("full_name", "email", "website")
	list_filter = ("enabled", )
	inlines = (AuthTokenInline, )
	exclude = ("tokens", )
