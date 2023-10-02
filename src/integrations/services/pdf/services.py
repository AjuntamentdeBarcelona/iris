import logging
from xml.dom import minidom
from .config import service_name, tag_1, tag_xml_1, tag_xml_2
from integrations.services.RestClient.integrate import ApiConnectClient
import json


class PdfServices(ApiConnectClient):

    def __init__(self, xml_file=False):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        self.tag_1 = tag_1
        self.tag_xml_1 = tag_xml_1
        self.tag_xml_2 = tag_xml_2
        self.xml_file = xml_file

    def create_xml(self, object, encoding=None):
        root = minidom.Document()
        if not self.xml_file:
            first = root.createElement(self.tag_1)
            root.appendChild(first)
        else:
            first_1 = root.createElement(self.tag_xml_1)
            root.appendChild(first_1)
            first = root.createElement(self.tag_xml_2)
            first_1.appendChild(first)
        for name in object:
            if (isinstance(object[name], list)):
                tag = root.createElement(name)
                first.appendChild(tag)
                for value in object[name][0]:
                    subtag = root.createElement(value)
                    subtag.appendChild(root.createTextNode(str(object[name][0][value])))
                    tag.appendChild(subtag)
            else:
                tag = root.createElement(name)
                tag.appendChild(root.createTextNode(str(object[name])))
                first.appendChild(tag)
        xml_str = root.toxml(encoding=encoding)
        xml_str = xml_str.decode(encoding=encoding) if encoding else xml_str
        xml_str = xml_str.replace('&gt;', '>')
        xml_str = xml_str.replace('&lt;', '<')
        return (xml_str)

    def construct_input_files(self, xml_data, rdto_data):
        files = {
                "rdto": ("rdto.json", json.dumps(rdto_data), 'application/json'),
                "dades": ("dades.xml", xml_data, 'text/xml'),
                }
        return files
