import logging

from jose import jwt
from social_core.backends.open_id_connect import OpenIdConnectAuth
from django.conf import settings

logger = logging.getLogger(__name__)


class IrisOpenIdConnect(OpenIdConnectAuth):
    name = 'iris-oidc'
    USERNAME_KEY = 'username'
    ID_KEY = 'username'
    ID_TOKEN_ISSUER = settings.OAUTH_AUTHORIZATION_URL
    AUTHORIZATION_URL = settings.OAUTH_AUTHORIZATION_URL
    ACCESS_TOKEN_URL = settings.OAUTH_ACCESS_TOKEN_URL
    USERINFO_URL = settings.OAUTH_USER_INFO_URL
    STATE_PARAMETER = False
    REDIRECT_STATE = False

    def validate_and_return_id_token(self, id_token, access_token):
        """
        todo: PCKE and verification
        """
        return jwt.get_unverified_claims(id_token)

    def get_redirect_uri(self, state=None):
        """
        todo: review this part
        """
        return settings.OAUTH_REDIRECT_LOGIN_URL

    def get_user_details(self, response):
        return {
            'username': self.get_username(response),
            'email': response['email'],
            'full_name': response['given_name'],
            'first_name': response.get('given_name'),
            'last_name': response.get('family_name'),
        }

    def get_user_id(self, details, response):
        return details.get(self.ID_KEY)

    def get_username(self, response):
        email = response['email']
        uuid = response['userid'].upper()
        logger.info(f'AUTH | USER WITH ID {uuid} | EMAIL {email}')
        return uuid
