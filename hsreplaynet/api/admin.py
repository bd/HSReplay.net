from django.contrib import admin
from hsreplaynet.uploads.models import UploadEvent
from hsreplaynet.utils.admin import set_user
from .models import APIKey, AuthToken


class UploadEventInline(admin.TabularInline):
	model = UploadEvent
	fields = ("game", "created", "file", "upload_ip", "status", "api_key")
	readonly_fields = fields[1:]
	raw_id_fields = ("game", )
	extra = 0
	show_change_link = True


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
	actions = (set_user, )
	date_hierarchy = "created"
	list_display = ("__str__", "user", "created")
	raw_id_fields = ("user", )
	inlines = (UploadEventInline, )


class AuthTokenInline(admin.TabularInline):
	model = APIKey.tokens.through
	raw_id_fields = ("authtoken", )
	extra = 3


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
	list_display = ("__str__", "email", "website", "api_key", "enabled")
	search_fields = ("full_name", "email", "website")
	list_filter = ("enabled", )
	inlines = (AuthTokenInline, )
	exclude = ("tokens", )
