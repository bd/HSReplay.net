from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class BattleNetAccount(ProviderAccount):
    pass


class BattleNetProvider(OAuth2Provider):
    id = 'battlenet'
    name = 'Battle.net'
    package = 'oauth.battlenet'
    account_class = BattleNetAccount

    def extract_uid(self, data):
        """ The data format will look like:
        {
            "id": 58054182,
            "battletag": "Nicodemus#1538"
        }

        """
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(username=data.get('battletag'),)

providers.registry.register(BattleNetProvider)