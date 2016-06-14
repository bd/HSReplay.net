from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.flatpages.views import flatpage
from django.views.generic import TemplateView


urlpatterns = [
	url(r"^$", TemplateView.as_view(template_name="home.html"), name="home"),
	url(r"^admin/", include(admin.site.urls)),
	url(r"^admin/", include("loginas.urls")),
	url(r"^api/", include("hsreplaynet.api.urls")),
	url(r"^about/privacy/$", flatpage, {"url": "/about/privacy/"}, name="privacy_policy"),
	url(r"^about/tos/$", flatpage, {"url": "/about/tos/"}, name="terms_of_service"),
	url(r"^account/", include("allauth_battlenet.urls")),
	url(r"^account/", include("allauth.urls")),
	url(r"^account/", include("hsreplaynet.accounts.urls")),
	url(r"^games/", include("hsreplaynet.games.urls")),
	url(r"^pages/", include("django.contrib.flatpages.urls")),
	url(r"^uploads/", include("hsreplaynet.uploads.urls")),
]


if settings.DEBUG:
	from django.conf.urls.static import static

	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
