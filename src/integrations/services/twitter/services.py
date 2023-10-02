from django.conf import settings
from integrations.services.RestClient.integrate import ApiConnectClient
from rest_framework.exceptions import ValidationError
from .config import user_path, message_path, service_name, message_error
import logging


class TwitterServices(ApiConnectClient):

    def __init__(self):
        self.consumer_key = settings.TWITTER_CONSUMER_KEY
        self.consumer_secret = settings.TWITTER_CONSUMER_SECRET
        self.access_token = settings.TWITTER_ACCESS_TOKEN
        self.token_secret = settings.TWITTER_TOKEN_SECRET
        self.client_id = settings.CLIENT_ID
        self.service_name = service_name
        self.headers = self.get_headers()

    def get_headers(self):
        logger = logging.getLogger(__name__)
        headers = {
            'x-oauth-consumer-key': self.consumer_key,
            'x-oauth-consumer-secret': self.consumer_secret,
            'x-oauth-access-token': self.access_token,
            'x-oauth-token-secret': self.token_secret,
            'x-ibm-client-id': self.client_id
        }
        logger.info(headers)
        return headers

    def get_user_data(self, username):
        params = {
            'screen_name': username
        }
        return ApiConnectClient(service_name, headers=self.headers).get(extension=user_path, params=params)

    def send_direct_message(self, username, text):
        username = username.replace('@', '')
        user_data = self.get_user_data(username)
        if not user_data.get('id', None):
            raise ValidationError({'__global__': message_error})
        json = {"event":
                {"type": "message_create",
                 "message_create": {"target": {"recipient_id": user_data['id']},
                                    "message_data": {"text": text}
                                    }
                 }
                }
        return ApiConnectClient(service_name, headers=self.headers).post(extension=message_path, json=json)
