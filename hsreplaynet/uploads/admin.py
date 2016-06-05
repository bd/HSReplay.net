from django.contrib import admin
from hsreplaynet.utils.admin import admin_urlify as urlify
from .models import GameUpload


@admin.register(GameUpload)
class AuthTokenAdmin(admin.ModelAdmin):
	date_hierarchy = "created"
	list_display = (
		"__str__", "status", "tainted", "type", urlify("token"),
		urlify("game"), "upload_ip", "file"
	)
	list_filter = ("type", "status", "tainted")
	raw_id_fields = ("token", "game")
