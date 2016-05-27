from django.conf.urls import url
from .views import UploadDetailView


urlpatterns = [
	url(r"^upload/(?P<id>[\w-]+)/$", UploadDetailView.as_view(), name="upload_detail"),
]
