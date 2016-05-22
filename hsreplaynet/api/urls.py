from django.conf.urls import url, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from . import legacy_views, views


router = DefaultRouter()
router.register(r"agents", views.UploadAgentViewSet)
router.register(r"tokens", views.AuthTokenViewSet)

urlpatterns = [
	url(r"^", include(router.urls)),
	url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]

urlpatterns += [
	url(r"^docs/$", TemplateView.as_view(template_name="api_docs.html")),
	url(r"^v1/replay/(?P<id>[\w-]+)$", legacy_views.fetch_replay, name="fetch_replay"),
	url(r"^v1/agents/(?P<api_key>[\w-]+)/attach_upload_token/(?P<token>[\w-]+)/$",
		legacy_views.AttachSiteUploadTokenView.as_view(), name="attach_site_upload_token"),
]
