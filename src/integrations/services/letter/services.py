import logging
import shutil
from integrations.services.pdf.services import PdfServices
from django.conf import settings
from .config import service_name
from integrations.services.RestClient.integrate import ApiConnectClient


class LetterServices(ApiConnectClient):

    def __init__(self, xml_file=False):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        self.xml_file = xml_file

    def send_to_report(self, json_data, rdto_data):
        xml_data = PdfServices.create_xml(json_data)
        files = PdfServices.construct_input_files(xml_data, rdto_data)
        self.logger.info(xml_data)
        headers = {
            'Accept': 'application/octet-stream',
            'X-IBM-Client-Id': settings.CLIENT_ID,
        }
        result = ApiConnectClient(self.service_name, headers=headers, logger=self.logger)
        result = result.post(files=files)
        return result

    def send_letters(self, pdf_file_name, pdf_path, xml_object):
        xml_str = PdfServices.create_xml(xml_object)
        xml_file_name = pdf_file_name.replace(".pdf", ".xml")
        with open(pdf_path + xml_file_name, "w") as f:
            f.write(xml_str)
            f.close()
        shutil.move(pdf_path + xml_file_name, self.destination_path + xml_file_name)
        shutil.move(pdf_path + pdf_file_name, self.destination_path + pdf_file_name)
