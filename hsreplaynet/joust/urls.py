from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^$', JoustStartupView.as_view(), name='joust_replay_list'),
    url(r'^collection/$', JoustPrivateCollectionView.as_view(), name='private_replay_collection'),
    url(r'^replay/(?P<id>[\w-]+)$', ReplayDetailView.as_view(), name='joust_replay_view'),
]