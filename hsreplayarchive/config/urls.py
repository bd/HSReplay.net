from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^$', 'web.views.home', name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include('web.urls')),
    url(r'^joust/', include('joust.urls')),
    url(r'^accounts/', include('allauth.urls')),
]
