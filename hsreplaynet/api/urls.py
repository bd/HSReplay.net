from django.conf.urls import url, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r"agents", views.UploadAgentViewSet)
router.register(r"tokens", views.AuthTokenViewSet)

urlpatterns = [
	url(r"^v1/", include(router.urls)),
	url(r"^v1/claim_account/", views.CreateAccountClaimView.as_view()),
	url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]

urlpatterns += [
	url(r"^docs/$", TemplateView.as_view(template_name="api_docs.html")),
]
