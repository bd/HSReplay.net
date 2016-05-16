from django.conf.urls import url
from django.views.generic import RedirectView
from .views import *


urlpatterns = [
	url(r"^$", RedirectView.as_view(pattern_name="my_replays", permanent=False)),
	url(r"^mine/$", JoustPrivateCollectionView.as_view(), name="my_replays"),
	url(r"^replay/(?P<id>[\w-]+)$", ReplayDetailView.as_view(), name="joust_replay_view"),
]
