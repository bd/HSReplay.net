from django.conf.urls import url
from ..views import *


urlpatterns = [
    url(r'^v1/replay/(?P<id>[\w-]+)$', fetch_replay, name='fetch_replay'),
    url(r'^v1/agents/generate_single_site_upload_token/$',
        GenerateSingleSiteUploadTokenView.as_view(), name='generate_single_site_upload_token'),
    url(r'^v1/agents/(?P<api_key>[\w-]+)/attach_upload_token/(?P<single_site_upload_token>[\w-]+)/$',
        AttachSiteUploadTokenView.as_view(), name='attach_site_upload_token'),
    url(r'^v1/agents/upload_token/(?P<single_site_upload_token>[\w-]+)/$',
        UploadTokenDetailsView.as_view(), name='upload_token_details_view'),
]
