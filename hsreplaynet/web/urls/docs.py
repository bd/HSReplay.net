from django.conf.urls import url
from ..views import ContributeView


urlpatterns = [
	url(r"^contribute/(?P<method>[\w]+)/$", ContributeView.as_view(), name="contribute"),
]
