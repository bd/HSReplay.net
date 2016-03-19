""" A Battle.net OAuth2 provider for the django-allauth package.

This package is modeled after other socialaccount providers. Reference resources:

The forum for Battle.net API related issues:

http://us.battle.net/en/forum/15051532/

Another Django Library Demonstrating the Battle.net OAuth2 process:

https://github.com/chrisgibson17/django-battlenet-oauth2/blob/master/battlenet/oauth2/__init__.py

Battle.net's interactive API docs:

https://dev.battle.net/io-docs
"""
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
import requests
from .provider import BattleNetProvider
from web.models import SingleSiteUploadToken
from django.shortcuts import render


class BattleNetOAuth2Adapter(OAuth2Adapter):
    provider_id = BattleNetProvider.id
    supports_state = True

    @property
    def access_token_url(self):
        return 'https://us.battle.net/oauth/token'

    @property
    def authorize_url(self):
        return 'https://us.battle.net/oauth/authorize'

    @property
    def profile_url(self):
        return 'https://us.api.battle.net/account/user'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url, params={ 'access_token': token.token })
        extra_data = resp.json()
        sociallogin = self.get_provider().sociallogin_from_response(request, extra_data)

        if 'token_attachment_requested' in request.session:
            api_key = request.session['api_key']
            upload_token = request.session['upload_token']
            token = SingleSiteUploadToken.objects.get(token=upload_token)
            token.user = sociallogin.user
            token.save()
            return render(request, 'web/token_attached.html', {'token': str(token.token)})

        return sociallogin

oauth2_login = OAuth2LoginView.adapter_view(BattleNetOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BattleNetOAuth2Adapter)