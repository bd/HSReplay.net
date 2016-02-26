from django.conf.urls import include, url

urlpatterns = [
    url(r'^$', 'web.views.home', name='home'),
    url(r'^api/', include('web.urls')),
    url(r'^joust/', include('joust.urls')),
    url(r'^user/', include('user.urls', app_name='user', namespace='hsreplayarchive-auth')),
]
