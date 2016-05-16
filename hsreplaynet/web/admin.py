from django.contrib import admin
from .models import *


@admin.register(SingleGameRawLogUpload)
class SingleGameRawLogUploadAdmin(admin.ModelAdmin):
	pass


@admin.register(SingleSiteUploadToken)
class SingleSiteUploadTokenAdmin(admin.ModelAdmin):
	raw_id_fields = ("user", )


@admin.register(UploadAgentAPIKey)
class UploadAgentAPIKeyAdmin(admin.ModelAdmin):
	pass
