from django.conf.urls import url
from .views import JoustStartupView, ReplayDetailView

urlpatterns = [
    url(r'^$', JoustStartupView.as_view(), name='joust_startup_view'),
    url(r'^replay/(?P<id>[\w-]+)$', ReplayDetailView.as_view(), name='joust_replay_view'),
]