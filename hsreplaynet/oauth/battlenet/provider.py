from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from web.models import SingleSiteUploadToken


class BattleNetSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if 'battletag' in data:
            user.username = data["battletag"]
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.username = sociallogin.account.extra_data['battletag']
        user.save()

        # Complete attachment of a token if one was requested prior to signup.
        if 'token_attachment_requested' in request.session:
            api_key = request.session['api_key']
            upload_token = request.session['upload_token']
            token = SingleSiteUploadToken.objects.get(token=upload_token)
            token.user = user
            token.save()

        return user


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