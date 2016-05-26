from django.contrib import admin
from hsreplaynet.utils import admin_urlify as urlify
from .models import GameUpload


@admin.register(GameUpload)
class AuthTokenAdmin(admin.ModelAdmin):
	date_hierarchy = "created"
	list_display = (
		"__str__", "failed", "type", urlify("token"),
		urlify("game"), "upload_ip", "file"
	)
	list_filter = ("type", "failed")
	raw_id_fields = ("token", "game")
