from django.conf.urls import url
from .views import ReplayUploadView, fetch_replay, ContributeView

urlpatterns = [
    url(r'^v1/replay/upload$', ReplayUploadView.as_view(), name='replay_upload_view_v1'),
    url(r'^v1/replay/(?P<id>[\w-]+)$', fetch_replay, name='fetch_replay'),
    url(r'^v1/docs/contribute/(?P<method>[\w]+)/$', ContributeView.as_view(), name='contribute'),
]