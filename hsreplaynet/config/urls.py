from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView
from web.urls import api, docs
from web.views import home


urlpatterns = [
	url(r"^$", home, name="home"),
	url(r"^admin/", include(admin.site.urls)),
	url(r"^api/", include(api)),
	url(r"^docs/", include(docs)),
	url(r"^games/", include("joust.urls")),
	url(r"^account/$",
		TemplateView.as_view(template_name="account/edit.html"),
		name="account_edit"
	),
	url(r"^account/", include("allauth_battlenet.urls")),
	url(r"^account/", include("allauth.urls")),
	url(r"^pages/", include("django.contrib.flatpages.urls")),
]
