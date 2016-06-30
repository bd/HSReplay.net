from django.contrib import admin
from hsreplaynet.utils.admin import admin_urlify as urlify
from .models import UploadEvent
from .processing import queue_upload_event_for_processing


def queue_for_reprocessing(admin, request, queryset):
	for obj in queryset:
		queue_upload_event_for_processing(str(obj.id))
queue_for_reprocessing.short_description = "Queue for reprocessing"


@admin.register(UploadEvent)
class UploadEventAdmin(admin.ModelAdmin):
	actions = (queue_for_reprocessing, )
	date_hierarchy = "created"
	list_display = (
		"__str__", "status", "tainted", "type", urlify("token"),
		urlify("game"), "upload_ip", "created", "file",
	)
	list_filter = ("type", "status", "tainted")
	raw_id_fields = ("token", "game")
	readonly_fields = ("created", )
	search_fields = ("shortid", )
