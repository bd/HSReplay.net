from django.conf.urls import url
from .views import ReplayDetailView

urlpatterns = [
    url(r'^$', ReplayDetailView.as_view(), name='joust_replay_detail_view'),
]