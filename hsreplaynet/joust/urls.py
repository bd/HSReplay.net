from django.conf.urls import url
from django.views.generic import RedirectView
from .views import *


urlpatterns = [
	url(r"^$", RedirectView.as_view(pattern_name="private_replay_collection")),
	url(r"^collection/$", JoustPrivateCollectionView.as_view(), name="private_replay_collection"),
	url(r"^replay/(?P<id>[\w-]+)$", ReplayDetailView.as_view(), name="joust_replay_view"),
]
