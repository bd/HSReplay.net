from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from . import legacy_views, views


router = DefaultRouter()
router.register(r"tokens", views.UploadTokenViewSet)

urlpatterns = [
	url(r"^", include(router.urls)),
	url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]

urlpatterns += [
	url(r"^docs/$", legacy_views.APIDocsView.as_view()),
	url(r"^v1/replay/(?P<id>[\w-]+)$", legacy_views.fetch_replay, name="fetch_replay"),
	url(r"^v1/agents/generate_single_site_upload_token/$",
		legacy_views.GenerateAuthTokenView.as_view(), name="generate_auth_token"),
	url(r"^v1/agents/(?P<api_key>[\w-]+)/attach_upload_token/(?P<token>[\w-]+)/$",
		legacy_views.AttachSiteUploadTokenView.as_view(), name="attach_site_upload_token"),
	url(r"^v1/agents/upload_token/(?P<token>[\w-]+)/$",
		legacy_views.UploadTokenDetailsView.as_view(), name="upload_token_details_view"),
]
