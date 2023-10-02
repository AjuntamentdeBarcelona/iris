from integrations.services.sms.config import service_name, send_sms
from integrations.services.RestClient.integrate import ApiConnectClient
import logging


class SmsServices(ApiConnectClient):

    def __init__(self):
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)

    def send_sms(self, message, telephone, application='IRIS', destination='ajunt BCN',
                 user='', simulation=True, buroSMS='false'):
        json = {
            "aplicacion": application,
            "buroSMS": buroSMS,
            "mensaje": message,
            "remitente": destination,
            "simulacion": simulation,
            "telefono": telephone,
            "usuario": user,
        }
        self.logger.info('Sms send json: %s', json)
        data = ApiConnectClient(self.service_name, logger=self.logger)
        result = data.post(extension=send_sms, json=json)
        self.logger.info('Sms send request: %s', result.request)
        self.logger.info('Sms send headers: %s', result.request.headers)
        self.logger.info('Sms send to url: %s', result.request.url)
        self.logger.info('Sms send response content: %s', result.content)
        self.logger.info('Sms send response result: %s', result)
        self.logger.info('Sms send result: %s', result.json())
        return result.json()
