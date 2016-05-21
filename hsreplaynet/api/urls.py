from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from .legacy_views import APIDocsView
from . import views


router = DefaultRouter()
router.register(r"tokens", views.UploadTokenViewSet)

urlpatterns = [
	url(r"^", include(router.urls)),
	url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
	url(r"^docs/$", APIDocsView.as_view()),
]
