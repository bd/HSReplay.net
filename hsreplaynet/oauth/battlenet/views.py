"""
The forum for Battle.net API related issues: http://us.battle.net/en/forum/15051532/
A Django Library Example: https://github.com/chrisgibson17/django-battlenet-oauth2/blob/master/battlenet/oauth2/__init__.py

Example of requesting a user's account:
https://us.api.battle.net/account/user?access_token=5cxewm47vaqfm78nj8qpzf6n
Response:

{
    "id": 58054182,
    "battletag": "Nicodemus#1538"
}

These are also useful for testing: https://dev.battle.net/io-docs

https://us.battle.net/oauth/authorize?client_id=jk94yjkz6nhkkvtjjuvkan3jmsbfxqj9&redirect_uri=https%3A%2F%2Fdev.battle.net%2Fio-docs%2Foauth2callback&response_type=code&scope=wow.profile+sc2.profile
https://us.battle.net/oauth/authorize?client_id=jk94yjkz6nhkkvtjjuvkan3jmsbfxqj9&state=Cq2UWPjYPobb&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Faccounts%2Fbattlenet%2Flogin%2Fcallback%2F&response_type=code&scope=wow.profile
"""
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
import requests
from .provider import BattleNetProvider


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
        resp = requests.get(self.profile_url,
                            params={ 'access_token': token.token })
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(BattleNetOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BattleNetOAuth2Adapter)