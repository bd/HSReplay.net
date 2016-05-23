from django.conf.urls import url
from django.views.generic import RedirectView
from .views import MyReplaysView, ReplayDetailView


# NOTE: Remove this once we have short IDs
UUID = r"[0-9a-f-]{36}"

urlpatterns = [
	url(r"^$", RedirectView.as_view(pattern_name="my_replays", permanent=False)),
	url(r"^mine/$", MyReplaysView.as_view(), name="my_replays"),
	url(r"^replay/(?P<id>%s)$" % (UUID), ReplayDetailView.as_view(), name="games_replay_view"),
]
