from django.conf.urls import url
from .views import ReplayUploadView

urlpatterns = [
    url(r'^v1/replay/upload$', ReplayUploadView.as_view(), name='replay_upload_view_v1'),
]