from django.conf.urls import url
from django.views.generic import TemplateView
from .views import *


urlpatterns = [
	url(r"^delete/$", TemplateView.as_view(template_name="account/delete.html"), name="account_delete"),
]
