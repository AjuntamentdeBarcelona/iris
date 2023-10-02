import csv
from xml.etree.ElementTree import Element, SubElement, ElementTree as ET
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import logging
import io
import pysftp


class FilesTools:

    def __init__(self, queryset_class, call=True):
        self.logger = logging.getLogger(__name__)
        if call is True:
            self.queryset = queryset_class()
        else:
            self.queryset = queryset_class
        self.sftp_hostname = settings.SFTP_HOSTNAME
        self.sftp_username = settings.SFTP_USERNAME
        self.sftp_password = settings.SFTP_PASSWORD
        self.sftp_dest_path = settings.SFTP_PATH

    def file_writer(self, file_name, queryset_func, delimiter='|', quotechar='', quoting=csv.QUOTE_NONE,
                    encoding='cp1252', escapechar='', add_headers=True, xml=False, lineterminator=False,
                    move_to_sftp=False):
        self.log(file_name, 'Generating Report File in temp file')
        self.log(queryset_func, 'Using function')
        data = self.queryset.select_function(queryset_func)
        if data:
            self.log(file_name, 'Removing the old File in temp file')
            default_storage.delete(file_name)
        real_file_name = file_name.split('/')[-1]
        temp_file_name = '/tmp/' + real_file_name
        self.log(file_name, 'Defining real and temp file name')
        with open(temp_file_name, 'w', encoding=encoding) as csv_file:
            self.log(file_name, 'Opening temp file')
            if not data:
                self.log(file_name, 'Is an empty file {}')
            else:
                self.log(file_name, 'Writing to minio')
                self.write_csv_minio(lineterminator, csv_file, delimiter, quotechar, quoting, escapechar,
                                     add_headers, data, temp_file_name, file_name)
            self.log(temp_file_name, 'file path {}')
            if move_to_sftp:
                carpet = file_name.split('/')[0]
                self.move_to_sftp(temp_file_name, self.sftp_dest_path, real_file_name, carpet)
        if xml:
            temp_file_name = temp_file_name.replace('csv', 'xml').replace('CVS', 'XML')
            file_name = file_name.replace('csv', 'xml').replace('CVS', 'XML')
            with open(temp_file_name, 'w', encoding=encoding) as csv_file:
                if not data:
                    self.log(file_name, 'Is an empty file {}')
                else:
                    self.write_xml(csv_file, temp_file_name, file_name, data)

    def add_header_keys(self, data):
        keys_result = []
        for key in data[0].keys():
            if 'SPACE' in key:
                key = ''
            keys_result.append(key)
        return keys_result

    def result_data_transform(self, sub_data):
        result_data = []
        for value in sub_data.values():
            if not str(value).strip() and False:
                value = ''
            result_data.append(value)
        return result_data

    def file_writer_partition(self, file_name, queryset_func, delimiter='|', quotechar='',
                              quoting=csv.QUOTE_NONE, encoding='cp1252', escapechar='',
                              add_headers=True, xml=False, lineterminator=False,
                              move_to_sftp=False):
        self.log(file_name, 'Generating Report File in temp file')
        self.log(queryset_func, 'Using function')
        default_storage.delete(file_name)
        self.log(file_name, 'Defining real and temp file name')
        if xml:
            self.partition_with_xml(file_name, queryset_func, encoding,
                                    lineterminator, delimiter, quotechar,
                                    quoting, escapechar, move_to_sftp, add_headers)
        else:
            self.partition_without_xml(file_name, queryset_func, encoding,
                                       lineterminator, delimiter, quotechar,
                                       quoting, escapechar, move_to_sftp, add_headers)

    def bi_file_writer_partition(self, file_name, queryset_func, delimiter='|', quotechar='',
                                 quoting=csv.QUOTE_NONE, encoding='cp1252', escapechar='',
                                 add_headers=True, xml=False, lineterminator=False,
                                 move_to_sftp=False, first_case=True, page_inici=0, page_final=None):
        self.log(file_name, 'Generating Report File in temp file')
        self.log(queryset_func, 'Using function')
        if first_case:
            default_storage.delete(file_name)
        self.log(file_name, 'Defining real and temp file name')
        self.bi_partition_without_xml(file_name, queryset_func, encoding,
                                      lineterminator, delimiter, quotechar,
                                      quoting, escapechar, move_to_sftp,
                                      add_headers, first_case, page_inici, page_final)

    def partition_without_xml(self, file_name, queryset_func, encoding,
                              lineterminator, delimiter, quotechar,
                              quoting, escapechar, move_to_sftp, add_headers):
        page = 0
        real_file_name = file_name.split('/')[-1]
        temp_file_name = '/tmp/' + real_file_name
        with open(temp_file_name, 'w', encoding=encoding) as csv_file:
                data = self.queryset.select_function(queryset_func, page)
                while data:
                    self.logger.info(page)
                    if lineterminator:
                        wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar,
                                        quoting=quoting, lineterminator='\n', escapechar=escapechar)
                    else:
                        wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar, quoting=quoting)
                    if add_headers:
                        self.log(file_name, 'Adding headers to csv')
                        keys_result = self.add_header_keys(data)
                        wr.writerow(keys_result)
                    for sub_data in data:
                        result_data = self.result_data_transform(sub_data)
                        wr.writerow(result_data)
                    add_headers = False
                    page += 1
                    data = self.queryset.select_function(queryset_func, page)
                self.write_to_minio(csv_file, temp_file_name, file_name)
                if move_to_sftp:
                    carpet = file_name.split('/')[0]
                    self.move_to_sftp(temp_file_name, self.sftp_dest_path, real_file_name, carpet)

    def bi_partition_without_xml(self, file_name, queryset_func, encoding,
                                 lineterminator, delimiter, quotechar,
                                 quoting, escapechar, move_to_sftp, add_headers, first_case,
                                 page_inici,
                                 page_final):
        page = page_inici
        real_file_name = file_name.split('/')[-1]
        temp_file_name = '/tmp/' + real_file_name
        previous_text = default_storage.open(file_name).read() if not first_case else None
        page_final = 10000 if not page_final else page_final
        with open(temp_file_name, 'w', encoding=encoding) as csv_file:
                data = self.queryset.select_function(queryset_func, page)
                while data and page < page_final:
                    if previous_text and page == page_inici:
                        self.logger.info(previous_text.decode(encoding))
                        csv_file.write(previous_text.decode(encoding))
                    if lineterminator:
                        wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar,
                                        quoting=quoting, lineterminator='\n', escapechar=escapechar)
                    else:
                        wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar, quoting=quoting)
                    if add_headers:
                        self.log(file_name, 'Adding headers to csv')
                        keys_result = self.add_header_keys(data)
                        wr.writerow(keys_result)
                    for sub_data in data:
                        result_data = self.result_data_transform(sub_data)
                        wr.writerow(result_data)
                    add_headers = False
                    page += 1
                    data = self.queryset.select_function(queryset_func, page)
                self.write_to_minio(csv_file, temp_file_name, file_name)
                if move_to_sftp:
                    carpet = file_name.split('/')[0]
                    self.move_to_sftp(temp_file_name, self.sftp_dest_path, real_file_name, carpet)

    def partition_with_xml(self, file_name, queryset_func, encoding,
                           lineterminator, delimiter, quotechar,
                           quoting, escapechar, move_to_sftp, add_headers):
        page = 0
        real_file_name = file_name.split('/')[-1]
        temp_file_name = '/tmp/' + real_file_name
        t = temp_file_name
        enc = encoding
        xml_temp_file_name = temp_file_name.replace('csv', 'xml').replace('CVS', 'XML')
        x_t = xml_temp_file_name
        xml_file_name = file_name.replace('csv', 'xml').replace('CVS', 'XML')
        self.logger.info(f"Opening file {real_file_name}")
        data = self.queryset.select_function(queryset_func, page)
        while data:
            page += 1
            data = self.queryset.select_function(queryset_func, page)
        page = 0
        with open(t, 'w', encoding=enc) as csv_file, open(x_t, 'w', encoding=encoding) as xml_file:
            data = self.queryset.select_function('insert_opendata_into_file', page)
            while data:
                self.logger.info(f"Inserting data of page {page} into {real_file_name}")
                if lineterminator:
                    wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar,
                                    quoting=quoting, lineterminator='\n', escapechar=escapechar)
                else:
                    wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar, quoting=quoting)
                if add_headers:
                    keys_result = self.add_header_keys(data)
                    wr.writerow(keys_result)
                for sub_data in data:
                    result_data = self.result_data_transform(sub_data)
                    wr.writerow(result_data)
                add_headers = False
                page += 1
                reparsed_string = self.get_xml_tree(data)
                xml_file.write(reparsed_string)
                self.logger.info(f"Checking for data of page {page}")
                data = self.queryset.select_function('insert_opendata_into_file', page)
            self.logger.info(f"Uploading {real_file_name} into minio")
            self.write_to_minio(xml_file, xml_temp_file_name, xml_file_name)
            self.write_to_minio(csv_file, temp_file_name, file_name)
            if move_to_sftp:
                self.logger.info(f"SFTP Moving {real_file_name}")
                carpet = file_name.split('/')[0]
                year = real_file_name[-8:-4]
                real_file_name = str(year) + '_IRIS_Peticions_Ciutadanes_OpenData.csv'
                xml_real_file_name = str(year) + '_IRIS_Peticions_Ciutadanes_OpenData.xml'
                self.move_to_sftp(temp_file_name, self.sftp_dest_path, real_file_name, carpet)
                self.move_to_sftp(xml_temp_file_name, self.sftp_dest_path, xml_real_file_name, carpet)

    def write_csv_minio(self, lineterminator, csv_file, delimiter, quotechar, quoting, escapechar,
                        add_headers, data, temp_file_name, file_name):
                    self.log(file_name, 'Starting writing to csv')
                    if lineterminator:
                        wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar,
                                        quoting=quoting, lineterminator='\n', escapechar=escapechar)
                    else:
                        wr = csv.writer(csv_file, delimiter=delimiter, quotechar=quotechar, quoting=quoting)
                    if add_headers:
                        self.log(file_name, 'Adding headers to csv')
                        keys_result = []
                        for key in data[0].keys():
                            if 'SPACE' in key:
                                key = ''
                            keys_result.append(key)
                        wr.writerow(keys_result)
                    for sub_data in data:
                        result_data = []
                        for value in sub_data.values():
                            if not str(value).strip() and False:
                                value = ''
                            result_data.append(value)
                        wr.writerow(result_data)
                    self.log(file_name, 'Report saved')
                    self.write_to_minio(csv_file, temp_file_name, file_name)

    def write_xml(self, csv_file, temp_file_name, file_name, data):
        reparsed_string = self.get_xml_tree(data)
        csv_file.write(reparsed_string)
        self.log(file_name, 'Report saved')
        self.write_to_minio(csv_file, temp_file_name, file_name)

    def move_to_sftp(self, file_path, dest_path, real_file_name, carpet):
        if carpet == 'biiris':
            carpet = 'BI'
        elif carpet == 'mib':
            carpet = 'MIB'
        elif carpet == 'bimap':
            carpet = 'BIMAP'
        elif carpet == 'opendata_views':
            carpet = 'OPENDATA'
        file_name = carpet + '/' + real_file_name
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(host=self.sftp_hostname,
                               username=self.sftp_username,
                               password=self.sftp_password,
                               cnopts=cnopts) as sftp:
            self.logger.info(f'MOVING| {file_path} to {dest_path}{file_name}')
            sftp.put(file_path, dest_path+file_name)

    def write_to_minio(self, csv_file, temp_file_name, file_name):
        csv_file.flush()
        with open(temp_file_name, 'rb') as temp_file:
            buffer = io.BytesIO(temp_file.read())
        default_storage.save(file_name, ContentFile(buffer.getvalue()))

    def get_xml_tree(self, data):
        top = Element('PETICIONS')
        for x in data:
            top_child = SubElement(top, 'PETICIO')
            row_child = SubElement(top_child, 'FITXA_ID')
            row_child.text = str(x.get('"FITXA_ID"'))
            row_child = SubElement(top_child, "TIPUS")
            row_child.text = str(x.get('"TIPUS"')).replace('"', '')
            row_child = SubElement(top_child, "AREA")
            row_child.text = str(x.get('"AREA"')).replace('"', '')
            row_child = SubElement(top_child, "ELEMENT")
            row_child.text = str(x.get('"ELEMENT"')).replace('"', '')
            row_child = SubElement(top_child, "DETALL")
            row_child.text = str(x.get('"DETALL"')).replace('"', '')
            row_child = SubElement(top_child, "DIA_DATA_ALTA")
            row_child.text = str(x.get('"DIA_DATA_ALTA"'))
            row_child = SubElement(top_child, "MES_DATA_ALTA")
            row_child.text = str(x.get('"MES_DATA_ALTA"'))
            row_child = SubElement(top_child, "ANY_DATA_ALTA")
            row_child.text = str(x.get('"ANY_DATA_ALTA"'))
            row_child = SubElement(top_child, "DIA_DATA_TANCAMENT")
            row_child.text = str(x.get('"DIA_DATA_TANCAMENT"'))
            row_child = SubElement(top_child, "MES_DATA_TANCAMENT")
            row_child.text = str(x.get('"MES_DATA_TANCAMENT"'))
            row_child = SubElement(top_child, "ANY_DATA_TANCAMENT")
            row_child.text = str(x.get('"ANY_DATA_TANCAMENT"'))
            row_child = SubElement(top_child, "CODI_DISTRICTE")
            row_child.text = str(x.get('"CODI_DISTRICTE"'))
            row_child = SubElement(top_child, "DISTRICTE")
            row_child.text = str(x.get('"DISTRICTE"')).replace('"', '')
            row_child = SubElement(top_child, "CODI_BARRI")
            row_child.text = str(x.get('"CODI_BARRI"'))
            row_child = SubElement(top_child, "BARRI")
            row_child.text = str(x.get('"BARRI"')).replace('"', '')
            row_child = SubElement(top_child, "SECCIO_CENSAL")
            row_child.text = str(x.get('"SECCIO_CENSAL"'))
            row_child = SubElement(top_child, "TIPUS_VIA")
            row_child.text = str(x.get('"TIPUS_VIA"')).replace('"', '')
            row_child = SubElement(top_child, "CARRER")
            row_child.text = str(x.get('"CARRER"')).replace('"', '')
            row_child = SubElement(top_child, "NUMERO")
            row_child.text = str(x.get('"NUMERO"'))
            row_child = SubElement(top_child, "COORDENADA_X")
            row_child.text = str(x.get('"COORDENADA_X"'))
            row_child = SubElement(top_child, "COORDENADA_Y")
            row_child.text = str(x.get('"COORDENADA_Y"'))
            row_child = SubElement(top_child, "LATITUD")
            row_child.text = str(x.get('"LATITUD"'))
            row_child = SubElement(top_child, "LONGITUD")
            row_child.text = str(x.get('"LONGITUD"'))
            row_child = SubElement(top_child, "SUPORT")
            row_child.text = str(x.get('"SUPORT"').replace('"', ''))
            row_child = SubElement(top_child, "CANALS_RESPOSTA")
            row_child.text = str(x.get('"CANALS_RESPOSTA"').replace('"', ''))
        tree = ET(top)
        tree = tree.getroot()
        reparsed = ElementTree.tostring(tree)
        reparsed = minidom.parseString(reparsed)
        reparsed_string = reparsed.toprettyxml(indent='', newl='', encoding='utf-8').decode('utf-8')
        return reparsed_string

    def validation(self):
        return []

    def log(self, file_name, txt):
        self.logger.info('REPORT | {} | {}'.format(file_name, txt))


def remove_code_and_send(file, dst, delimiter="|"):
    """
    When a report is validate, like OpenData, must be adapted for removing the record card code and the new file must be
    writen in the final destination. The record card code is the first column within the CSV file generated for
    validation.
    :param file:
    :param dst:
    :param delimiter:
    :return: file
    """
    content = default_storage.open(file).read()
    content = content.decode("utf-8")
    cont_file = ContentFile(content)
    reader = csv.DictReader(cont_file, delimiter=delimiter)
    default_storage.delete(dst)

    dest_file = io.StringIO()

    field_names = [field_name for field_name in reader.fieldnames if field_name != "CODI"]
    writer = csv.DictWriter(dest_file, fieldnames=field_names)
    writer.writeheader()
    for row in reader:
        row.pop("CODI", None)
        writer.writerow(row)
    default_storage.save(dst, ContentFile(dest_file.getvalue().encode("utf-8")))
