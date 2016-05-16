from django.conf.urls import include, url
from django.contrib import admin
from web.urls import api, docs


urlpatterns = [
	url(r"^$", "web.views.home", name="home"),
	url(r"^admin/", include(admin.site.urls)),
	url(r"^api/", include(api)),
	url(r"^docs/", include(docs)),
	url(r"^games/", include("joust.urls")),
	url(r"^accounts/", include("allauth_battlenet.urls")),
	url(r"^accounts/", include("allauth.urls")),
]
