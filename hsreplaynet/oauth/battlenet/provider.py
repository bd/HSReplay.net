from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class BattleNetSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        sociallogin.account.user.username = data["battletag"]
        super().populate_user(request, sociallogin, data)


class BattleNetAccount(ProviderAccount):
    pass


class BattleNetProvider(OAuth2Provider):
    id = 'battlenet'
    name = 'Battle.net'
    package = 'oauth.battlenet'
    account_class = BattleNetAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(battletag=data.get('battletag'),)

providers.registry.register(BattleNetProvider)