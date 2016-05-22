from django.contrib import admin
from .models import *


@admin.register(SingleSiteUploadToken)
class SingleSiteUploadTokenAdmin(admin.ModelAdmin):
	list_display = ("__str__", "user", "created")
	raw_id_fields = ("user", )


@admin.register(UploadAgentAPIKey)
class UploadAgentAPIKeyAdmin(admin.ModelAdmin):
	list_display = ("__str__", "email", "website", "api_key")
	search_fields = ("full_name", "email", "website")
