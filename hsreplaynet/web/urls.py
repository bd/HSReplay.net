from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^v1/replay/upload$', ReplayUploadView.as_view(), name='replay_upload_view_v1'),
    url(r'^v1/replay/(?P<id>[\w-]+)$', fetch_replay, name='fetch_replay'),
    url(r'^v1/docs/contribute/(?P<method>[\w]+)/$', ContributeView.as_view(), name='contribute'),
    url(r'^v1/agents/generate_single_site_upload_token/$',
        GenerateSingleSiteUploadTokenView.as_view(), name='generate_single_site_upload_token'),
]