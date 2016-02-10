from django.conf.urls import include, url

urlpatterns = [
    url(r'^$', 'web.views.home', name='home'),
    url(r'^api/', include('web.urls')),
]
