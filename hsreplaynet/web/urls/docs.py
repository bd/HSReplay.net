from django.conf.urls import url
from web.views import *

urlpatterns = [
    url(r'^contribute/(?P<method>[\w]+)/$', ContributeView.as_view(), name='contribute'),
    url(r'^upload/raw/$', UploadRawReplayView.as_view(), name='upload_raw_replay_log'),
]