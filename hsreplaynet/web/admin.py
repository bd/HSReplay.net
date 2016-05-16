from django.contrib import admin
from .models import *


@admin.register(SingleGameRawLogUpload)
class SingleGameRawLogUploadAdmin(admin.ModelAdmin):
	pass
