import requests
import abc
import logging
from django.conf import settings


class BaseRestClient(metaclass=abc.ABCMeta):

    def __init__(self, base_url_ac):
        pass

    def post(self):
        pass

    def get(self):
        pass


class ApiConnectClient(BaseRestClient):

    def __init__(self, service_name, headers={}, logger=None, auth=None):
        self.service_name = service_name
        self.url_ac = settings.AC_INTEGRATIONS[self.service_name][1]["url"]
        self.url_pa = settings.AC_INTEGRATIONS[self.service_name][0]["url"]
        self.auth = auth
        self.base_url = settings.BASE_URL
        if headers:
            self.headers = headers
        else:
            self.headers = settings.AC_HEADERS
        self.logger = logger or logging.getLogger(__name__)

    def get_ac(self, extension='', params={}):
        return requests.get(self.url_ac + extension, verify=False, headers=self.headers, params=params, auth=self.auth)

    def get(self, extension='', params={}):
        try:
            data = requests.get(self.url_ac + extension, verify=False, headers=self.headers, params=params,
                                auth=self.auth).json()
            self.logger.info('connected with api connect')
        except Exception:
            headers = {}
            data = requests.get(self.url_pa + extension, verify=False, headers=headers, params=params,
                                auth=self.auth).json()
            self.logger.info('connected with public api')
        return data

    def post(self, extension='', json={}, files={}, params=None, data=None, timeout=None):

        data = requests.post(self.url_ac + extension, verify=False, headers=self.headers, json=json, files=files,
                             params=params, data=data, auth=self.auth, timeout=timeout)
        self.logger.info('connected with api connect')
        return data


class ApiClient:
    def __init__(self, service_name, extension='', headers={}, logger=None):
        self.service_name = service_name
        if extension:
            self.url = settings.EXT_INTEGRATIONS[self.service_name][extension]
        else:
            self.url = settings.EXT_INTEGRATIONS[self.service_name]

        if headers:
            self.headers = headers
        else:
            self.headers = settings.EXT_HEADERS

        self.logger = logger or logging.getLogger(__name__)

    def get(self, json={}, params={}):
        data = requests.get(self.url, verify=False, headers=self.headers, params=params, json=json).json()
        self.logger.info('connected with extern integration %s , %s', (self.service_name, data))
        return data

    def post(self, json={}, params={}):
        data = requests.post(self.url, verify=False, headers=self.headers, params=params, json=json)
        self.logger.info('connected with extern integration %s , %s', (self.service_name, data))
        return data
