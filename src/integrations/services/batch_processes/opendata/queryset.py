from datetime import datetime
from django.db.models import Q, Subquery
from record_cards.models import RecordCard, Request, RecordCardResponse
from themes.models import ElementDetail
from integrations.models import OpenDataModel
import logging
import copy
from django.db.models import Max
import csv


class OpenDataQuerySets:

    records_limit = 100

    def __init__(self, year=2020, trimester=1, batch_file=None, offset=False, create=False, to_validate=False):
        self.offset = offset
        self.logger = logging.getLogger(__name__)
        self.newest_date_limit, self.oldest_date_limit = self.set_limit_dates(year, trimester)
        self.limit_creating_at_date = self.set_limit_creating_at_date(year)
        self.year = year
        self.trimester = trimester
        self.create = create
        self.to_validate = to_validate
        if batch_file:
            self.update_batch_file_limits(batch_file)

    def update_batch_file_limits(self, batch_file):
        batch_file.oldest_date_limit = self.oldest_date_limit
        batch_file.newest_date_limit = self.newest_date_limit
        batch_file.save()

    @staticmethod
    def set_limit_dates(year, trimester):
        if trimester == 1:
            left_window = '01/01/' + str(year)[-2:] + ' 00:00:00'
            right_window = '31/03/' + str(year)[-2:] + ' 23:59:59'
        elif trimester == 2:
            left_window = '01/04/' + str(year)[-2:] + ' 00:00:00'
            right_window = '30/06/' + str(year)[-2:] + ' 23:59:59'
        elif trimester == 3:
            left_window = '01/07/' + str(year)[-2:] + ' 00:00:00'
            right_window = '30/09/' + str(year)[-2:] + ' 23:59:59'
        else:
            left_window = '01/10/' + str(year)[-2:] + ' 00:00:00'
            right_window = '31/12/' + str(year)[-2:] + ' 23:59:59'
        return right_window, left_window

    def set_limit_creating_at_date(self, year):
        return str('01/01/' + str(year-1)[-2:]) + ' 00:00:00'

    def select_function(self, function, page='NO'):
        if page != 'NO':
            return getattr(self, function)(page)
        else:
            return getattr(self, function)()

    def file_open_data(self, record_cards):
        """
        file data queryset for OpenData
        IRIS 1 process: ''
        Delimiter:,
        Els identificadors dels registres publicats al web han de tenir un identificador seqüencial que continuï
         la seqüencia d'IRIS1 (102-103-104....)
        Table Identificador IRS1
        utf-8
        CR LF ->>> lineterminator = '\n'->>writer = False
        def file_writer(self, file_name, queryset_func, delimiter='|', quotechar='',
        quoting=csv.QUOTE_NONE, encoding='cp1252', add_headers=True):
        """
        self.logger.info('Starting opendata queryset')
        support_dictionary = {'CORREU GENCAT': 'CORREU ELECTRÒNIC',
                              'FULL DE QUEIXA GUUR': 'FULLS QUEIXES I SUGGERIMENTS',
                              'FULLS QUEIXA BSM': 'FULLS QUEIXES I SUGGERIMENTS',
                              'FULLS QUEIXA BÚSTIES IMH': 'FULLS QUEIXES I SUGGERIMENTS',
                              'FULLS QUEIXA OMIC': 'FULLS QUEIXES I SUGGERIMENTS',
                              'INSTÀNCIA AMB SIGNATURES': 'INSTÀNCIA',
                              'INSTÀNCIA NO VINCULADA': 'INSTÀNCIA',
                              'RECLAMACIÓ INTERNA': {
                                  'CORREU GENCAT': 'CORREU ELECTRÒNIC',
                                  'FULL DE QUEIXA GUUR': 'FULLS QUEIXES I SUGGERIMENTS',
                                  'FULLS QUEIXA BSM': 'FULLS QUEIXES I SUGGERIMENTS',
                                  'FULLS QUEIXA BÚSTIES IMH': 'FULLS QUEIXES I SUGGERIMENTS',
                                  'FULLS QUEIXA OMIC': 'FULLS QUEIXES I SUGGERIMENTS',
                                  'INSTÀNCIA AMB SIGNATURES': 'INSTÀNCIA',
                                  'INSTÀNCIA NO VINCULADA': 'INSTÀNCIA'
                              }}
        result_array = []
        for record_card in record_cards:
            original_record_cards = RecordCard.objects.filter(
                Q(request_id=record_card.request_id) & ~Q(applicant_type_id=23) & Q(id__lte=record_card.id))
            id_list = [x['id'] for x in original_record_cards.values('id')]
            max_id = max(id_list) if id_list else 0
            original_record_card = original_record_cards.get(id=max_id)
            detail = record_card.element_detail
            record_type = record_card.record_type
            element = detail.element
            area = element.area
            ubication = record_card.ubication
            record_card_response = RecordCardResponse.objects.filter(record_card_id=record_card.id)
            response_channel = record_card_response.get(record_card_id=record_card.id).response_channel \
                if record_card_response else None
            last_support = record_card.support
            original_support = original_record_card.support
            support = last_support.description
            support = self.calculate_support(last_support, original_support, support, support_dictionary)
            result_dict = {
                '"FITXA_ID"': record_card.normalized_record_id,
                '"TIPUS"': '"' + record_type.description + '"',
                '"AREA"': '"' + area.description.replace(',', ' ') + '"',
                '"ELEMENT"': '"' + element.description.replace(',', ' ') + '"',
                '"DETALL"': '"' + detail.description.replace(',', ' ') + '"',
                '"DIA_DATA_ALTA"': str(
                    '0' + str(original_record_card.created_at.day))[-2:] if original_record_card.created_at else '',
                '"MES_DATA_ALTA"': str(
                    '0' + str(original_record_card.created_at.month))[-2:] if original_record_card.created_at else '',
                '"ANY_DATA_ALTA"': original_record_card.created_at.year,
                '"DIA_DATA_TANCAMENT"': str(
                    '0' + str(record_card.closing_date.day))[-2:] if record_card.closing_date else '',
                '"MES_DATA_TANCAMENT"': str(
                    '0' + str(record_card.closing_date.month))[-2:] if record_card.closing_date else '',
                '"ANY_DATA_TANCAMENT"': record_card.closing_date.year,
                '"DATA_TANCAMENT"': record_card.closing_date}

            result_dict = self.get_ubication(detail.allows_open_data_location,
                                             detail.allows_open_data_sensible_location, ubication, result_dict)

            result_dict['"SUPORT"'] = '"' + support + '"'
            response_channel_description = self.calculate_response_channel_desc(response_channel)
            result_dict['"CANALS_RESPOSTA"'] = self.calculate_response_channel(response_channel_description)
            result_array.append(result_dict)
        return result_array

    def calculate_response_channel_desc(self, response_channel):
        response_channel_description = response_channel.name if response_channel else ''
        return response_channel_description

    def calculate_support(self, last_support, original_support, support, support_dictionary):
        if 'RECLAMACIÓ INTERNA' == last_support.description:
            support = support_dictionary.get('RECLAMACIÓ INTERNA').get(original_support.description, support)
        else:
            support = support_dictionary.get(last_support.description, support)
        return support

    def calculate_response_channel(self, response_channel_description):
        if response_channel_description == 'CAP':
            result = '"NO VOL RESPOSTA"'
        else:
            result = '"' + response_channel_description + '"'
        return result

    def calculate_district_code(self, ubication):
        if ubication.district_id and 'no' not in str(ubication.district_id).lower():
            result = str('0' + str(ubication.district_id))[-2:]
        else:
            result = ubication.district_id
        return result

    def calculate_barri(self, ubication):
        if ubication.neighborhood_id and 'no' not in str(ubication.neighborhood_id).lower():
            result = str('0' + str(ubication.neighborhood_id))[-2:]
        else:
            result = ubication.neighborhood_id
        return result

    def calculate_seccio_censal(self, ubication):
        if ubication.research_zone and 'no' not in str(ubication.research_zone).lower():
            result = str('00' + str(ubication.research_zone))[-3:]
        else:
            result = ubication.research_zone
        return result

    def get_ubication(self, allows_open_data_location, allows_open_data_sensible_location, ubication, result_dict):
        if allows_open_data_location and ubication:
            result_dict['"CODI_DISTRICTE"'] = self.calculate_district_code(ubication)
            result_dict['"DISTRICTE"'] = '"' + str(ubication.district) + '"'
            result_dict['"CODI_BARRI"'] = self.calculate_barri(ubication)
            result_dict['"BARRI"'] = '"' + ubication.neighborhood.replace(',', ' ') + '"'
            result_dict['"SECCIO_CENSAL"'] = self.calculate_seccio_censal(ubication)
            result_dict['"TIPUS_VIA"'] = '"' + ubication.via_type + '"'
            result_dict['"CARRER"'] = '"' + self.upper_street(ubication.street) + '"'
            result_dict['"NUMERO"'] = ubication.street2
            if ubication.street2 and 'no' not in str(ubication.street2).lower():
                result_dict['"NUMERO"'] = str('000' + str(ubication.street2))[-4:]
            x, y = self.coords_calculation(ubication.xetrs89a, ubication.yetrs89a)
            result_dict['"COORDENADA_X"'] = x
            result_dict['"COORDENADA_Y"'] = y
            result_dict['"LONGITUD"'] = ubication.longitude
            result_dict['"LATITUD"'] = ubication.latitude
        else:
            result_dict['"CODI_DISTRICTE"'] = ''
            result_dict['"DISTRICTE"'] = ''
            result_dict['"CODI_BARRI"'] = ''
            result_dict['"BARRI"'] = ''
            result_dict['"SECCIO_CENSAL"'] = ''
            if allows_open_data_sensible_location and ubication:
                result_dict['"TIPUS_VIA"'] = '"' + ubication.via_type + '"'
                result_dict['"CARRER"'] = '"' + self.upper_street(ubication.street) + '"'
                result_dict['"NUMERO"'] = ubication.street2
                if ubication.street2 and 'no' not in str(ubication.street2).lower():
                    result_dict['"NUMERO"'] = str('000' + str(ubication.street2))[-4:]
                x, y = self.coords_calculation(ubication.xetrs89a, ubication.yetrs89a)
                result_dict['"COORDENADA_X"'] = x
                result_dict['"COORDENADA_Y"'] = y
                result_dict['"LONGITUD"'] = ubication.longitude
                result_dict['"LATITUD"'] = ubication.latitude
            else:
                result_dict['"TIPUS_VIA"'] = ''
                result_dict['"CARRER"'] = ''
                result_dict['"NUMERO"'] = ''
                result_dict['"COORDENADA_X"'] = ''
                result_dict['"COORDENADA_Y"'] = ''
                result_dict['"LONGITUD"'] = ''
                result_dict['"LATITUD"'] = ''
        return result_dict

    def coords_calculation(self, x, y):
        x_result = abs(int(x)) if x else ''
        y_result = abs(int(y)) if y else ''
        return x_result, y_result

    def upper_street(self, street):
        if street:
            street = street.lower()
            newStreet = ''
            for word in street.split(' '):
                if word not in ['i', 'de', 'la', 'del', 'dels', 'los', 'las']:
                    word = word.capitalize()
                if word.lower() in ['ii', 'iii', 'iv', 'ix', 'xx', 'xii', 'vi', 'vii', 'v', 'ixx']:
                    word = word.upper()
                newStreet = newStreet + word + ' '
            return newStreet.strip()
        else:
            return street

    def get_array_from_csv(self, path):
        result_array = []
        with open(path, 'r', errors='ignore') as csv_file:
            reader = csv.reader(csv_file)
            for x in reader:
                x = x[0].split(';')
                if len(x) == 25:
                    result_dict = {
                        '"FITXA_ID"': x[0],
                        '"TIPUS"': x[1],
                        '"AREA"': x[2],
                        '"ELEMENT"': x[3],
                        '"DETALL"': x[4],
                        '"DIA_DATA_ALTA"': x[5],
                        '"MES_DATA_ALTA"': x[6],
                        '"ANY_DATA_ALTA"': x[7],
                        '"DIA_DATA_TANCAMENT"': x[8],
                        '"MES_DATA_TANCAMENT"': x[9],
                        '"ANY_DATA_TANCAMENT"': 2020,
                        '"CODI_DISTRICTE"': x[11], '"DISTRICTE"': x[12],
                        '"CODI_BARRI"': x[13],
                        '"BARRI"': x[14],
                        '"SECCIO_CENSAL"': x[15],
                        '"TIPUS_VIA"': x[16],
                        '"CARRER"': x[17],
                        '"NUMERO"': x[18],
                        '"COORDENADA_X"': x[19],
                        '"COORDENADA_Y"': x[20],
                        '"LONGITUD"': x[21],
                        '"LATITUD"': x[22],
                        '"SUPORT"': x[23],
                        '"CANALS_RESPOSTA"': x[24]
                    }
                    result_array.append(result_dict)
            return result_array

    def definitive_validation(self, page):
        last_month = datetime.strptime(self.newest_date_limit, '%d/%m/%y %H:%M:%S').month
        first_month = datetime.strptime(self.oldest_date_limit, '%d/%m/%y %H:%M:%S').month
        result_array = []
        self.logger.info(f"OPENDATA | Entering to definitive_validation function with page {str(page)}")
        if self.check_validated(first_month, last_month, self.year) is False:
            id = OpenDataModel.objects.filter(validated=True).aggregate(Max('id'))
            id = id.get('id__max')
            id = id if id else 0
            self.logger.info(f"OPENDATA | Calculated max id in opendatamodel")
            records = OpenDataModel.objects.filter(closing_year=self.year, validated=True, id__lte=id)
            self.logger.info(f"OPENDATA | Selected opendata records with closing year {self.year} and validated")
            checked_view = self.check_view(first_month, last_month, self.year)
            self.logger.info(checked_view)
            if checked_view:
                self.logger.info(f"OPENDATA | Selecting the data that must be validated")
                validated_records = OpenDataModel.objects.filter(
                    closing_month__gte=('0' + str(first_month))[-2:],
                    closing_month__lte=('0' + str(last_month))[-2:],
                    closing_year=self.year, validated=False)
                result_array = self.add_record_to_array(result_array, validated_records, id)
                self.logger.info(f"OPENDATA | Validating the selected data")
                OpenDataModel.objects.filter(
                    closing_month__gte=('0' + str(first_month))[-2:],
                    closing_month__lte=('0' + str(last_month))[-2:],
                    closing_year=self.year, validated=False).update(validated=True)
                self.logger.info(f"OPENDATA | Validated the selected data")
                result_array = self.add_record_to_array(result_array, records, id)
                result_array = sorted(result_array, key=lambda x: (int(x['"ANY_DATA_TANCAMENT"']),
                                                                   int(x['"MES_DATA_TANCAMENT"']),
                                                                   int(x['"DIA_DATA_TANCAMENT"']),
                                                                   int(x['"ANY_DATA_ALTA"']),
                                                                   int(x['"MES_DATA_ALTA"']),
                                                                   int(x['"DIA_DATA_ALTA"'])
                                                                   ))
                return result_array
            else:
                result_array = self.partitioning(page)
                if not result_array:
                    self.logger.info(f"OPENDATA | There is no more data for this trimester")
                    self.create_records_partitioning()
                    self.logger.info(f"OPENDATA | Inserted trimester data validated into opendatamodel")
                    return result_array
                id = id + (page*1000)
                result_array = self.add_id_opendata(result_array, id)
                result_array = self.fix_result_array(result_array)
                return result_array
        else:
            self.log('Warning: Trimester already validated!')

    def fix_result_array(self, result_array):
        for x in result_array:
            x.pop('"VALIDATED"')
            x.pop('"FITXA_ID_NORMALITZAT"')
        return result_array

    def create_records_partitioning(self):
        page = 0
        id = OpenDataModel.objects.all().aggregate(Max('id'))
        id = id.get('id__max')
        id = id if id else 0
        result_array = self.partitioning(page)
        while result_array:
            result_array = self.add_id_opendata(result_array, id)
            self.create_records(result_array, create=True, validated=True)
            page += 1
            id = id + (page*1000)
            result_array = self.partitioning(page)
        return id

    def check_validated(self, first_month, last_month, year):
        validated = False
        len_trimester = len(OpenDataModel.objects.filter(closing_month__gte=('0' + str(first_month))[-2:],
                            closing_month__lte=('0' + str(last_month))[-2:], closing_year=year, validated=True))
        if len_trimester > 0:
            validated = True
        return validated

    def check_view(self, first_month, last_month, year):
        validated = False
        self.logger.info(f"OPENDATA | Checking data for this trimester")
        len_trimester = len(OpenDataModel.objects.filter(closing_month__gte=('0' + str(first_month))[-2:],
                            closing_month__lte=('0' + str(last_month))[-2:], closing_year=year))
        if len_trimester > 0:
            validated = True
        self.logger.info(f"OPENDATA | Checked data for this trimester")
        return validated

    def create_records(self, result_array, create=False, validated=False):
        if create is True:
            for x in result_array:
                id = x.get('"FITXA_ID"')
                OpenDataModel.objects.create(id=x.get('"FITXA_ID"'),
                                             normalized_record_id=x.get('"FITXA_ID_NORMALITZAT"', id),
                                             type=x.get('"TIPUS"'),
                                             area=x.get('"AREA"'),
                                             element=x.get('"ELEMENT"'),
                                             detail=x.get('"DETALL"'),
                                             created_day=x.get('"DIA_DATA_ALTA"'),
                                             created_month=x.get('"MES_DATA_ALTA"'),
                                             created_year=x.get('"ANY_DATA_ALTA"'),
                                             closing_day=x.get('"DIA_DATA_TANCAMENT"'),
                                             closing_month=x.get('"MES_DATA_TANCAMENT"'),
                                             closing_year=x.get('"ANY_DATA_TANCAMENT"'),
                                             district_id=x.get('"CODI_DISTRICTE"'),
                                             district=x.get('"DISTRICTE"'),
                                             neighborhood_id=x.get('"CODI_BARRI"'),
                                             neighborhood=x.get('"BARRI"'),
                                             research_zone=x.get('"SECCIO_CENSAL"'),
                                             via_type=x.get('"TIPUS_VIA"'),
                                             street=x.get('"CARRER"'),
                                             street2=x.get('"NUMERO"'),
                                             xetrs89a=x.get('"COORDENADA_X"'),
                                             yetrs89a=x.get('"COORDENADA_Y"'),
                                             longitude=x.get('"LONGITUD"'),
                                             latitude=x.get('"LATITUD"'),
                                             support=x.get('"SUPORT"'),
                                             response_channel=x.get('"CANALS_RESPOSTA"'),
                                             validated=validated)
                x.pop('"VALIDATED"')
                x.pop('"FITXA_ID_NORMALITZAT"')
        return result_array

    def add_id_opendata(self, result_dict, id):
        for x in result_dict:
            id = id + 1
            x.update({'"FITXA_ID_NORMALITZAT"': x.get('"FITXA_ID"')})
            x.update({'"VALIDATED"': True})
            x.update({'"FITXA_ID"': id})
        return result_dict

    def add_record_to_array(self, result_array, records, id):
        for record in records:
            result_dict = {
                '"FITXA_ID"': id,
                '"TIPUS"': record.type,
                '"AREA"': record.area,
                '"ELEMENT"': record.element,
                '"DETALL"': record.detail,
                '"DIA_DATA_ALTA"': record.created_day,
                '"MES_DATA_ALTA"': record.created_month,
                '"ANY_DATA_ALTA"': record.created_year,
                '"DIA_DATA_TANCAMENT"': record.closing_day,
                '"MES_DATA_TANCAMENT"': record.closing_month,
                '"ANY_DATA_TANCAMENT"': int(record.closing_year),
                '"CODI_DISTRICTE"': record.district_id,
                '"DISTRICTE"': record.district,
                '"CODI_BARRI"': record.neighborhood_id,
                '"BARRI"': record.neighborhood,
                '"SECCIO_CENSAL"': record.research_zone,
                '"TIPUS_VIA"': record.via_type,
                '"CARRER"': record.street,
                '"NUMERO"': record.street2,
                '"COORDENADA_X"': record.xetrs89a,
                '"COORDENADA_Y"': record.yetrs89a,
                '"LONGITUD"': record.longitude,
                '"LATITUD"': record.latitude,
                '"SUPORT"': record.support,
                '"CANALS_RESPOSTA"': record.response_channel
            }
            result_array.append(result_dict)
            id += 1
        return result_array

    def add_record_to_array_2(self, result_array, records):
        for record in records:
            result_dict = {}
            result_dict['"FITXA_ID"'] = record.id
            result_dict['"TIPUS"'] = record.type
            result_dict['"AREA"'] = record.area
            result_dict['"ELEMENT"'] = record.element
            result_dict['"DETALL"'] = record.detail
            result_dict['"DIA_DATA_ALTA"'] = record.created_day
            result_dict['"MES_DATA_ALTA"'] = record.created_month
            result_dict['"ANY_DATA_ALTA"'] = record.created_year
            result_dict['"DIA_DATA_TANCAMENT"'] = record.closing_day
            result_dict['"MES_DATA_TANCAMENT"'] = record.closing_month
            result_dict['"ANY_DATA_TANCAMENT"'] = int(record.closing_year)
            result_dict['"CODI_DISTRICTE"'] = record.district_id
            result_dict['"DISTRICTE"'] = record.district
            result_dict['"CODI_BARRI"'] = record.neighborhood_id
            result_dict['"BARRI"'] = record.neighborhood
            result_dict['"SECCIO_CENSAL"'] = record.research_zone
            result_dict['"TIPUS_VIA"'] = record.via_type
            result_dict['"CARRER"'] = record.street
            result_dict['"NUMERO"'] = record.street2
            result_dict['"COORDENADA_X"'] = record.xetrs89a
            result_dict['"COORDENADA_Y"'] = record.yetrs89a
            result_dict['"LONGITUD"'] = record.longitude
            result_dict['"LATITUD"'] = record.latitude
            result_dict['"SUPORT"'] = record.support
            result_dict['"CANALS_RESPOSTA"'] = record.response_channel
            result_array.append(result_dict)
        return result_array

    @staticmethod
    def only_fields():
        return ("created_at", "normalized_record_id", "pk", "record_type", "record_type__description",
                "element_detail", "element_detail__description", "element_detail__allows_open_data",
                "element_detail__allows_open_data_location", "element_detail__allows_open_data_sensible_location",
                "element_detail__element", "element_detail__element__description", "element_detail__element__area",
                "element_detail__element__area__description", "closing_date", "ubication", "ubication__district",
                "ubication__district__name", "ubication__geocode_district_id", "ubication__neighborhood_id",
                "ubication__neighborhood", "ubication__research_zone", "ubication__via_type", "ubication__street",
                "ubication__street2", "ubication__xetrs89a", "ubication__yetrs89a", "ubication__longitude",
                "ubication__latitude", "support", "support__description", "recordcardresponse",
                "recordcardresponse__response_channel", "recordcardresponse__response_channel__name")

    def log(self, txt):
        self.logger.info("OPENDATA | {}".format(txt))

    def insert_opendata_into_file(self, page):
        result_array = []
        def_page = str(page * 1000).replace(';', '')
        params = [str(self.year), def_page]
        query = """select f1.* from integrations_opendatamodel f1
        where f1.closing_year = %s and f1.validated=True
        order by f1.closing_year, f1.closing_month, f1.closing_day, f1.created_year,
        f1.created_month, f1.created_day
        limit 1000 offset %s
        """
        Alias1 = OpenDataModel.objects.raw(query, params)
        result_array = self.add_record_to_array_2(result_array, Alias1)
        return result_array

    def partitioning(self, page):
        result_array = []
        Alias1 = self.query_count(page)
        result = len(Alias1)
        if result == 0:
            return result_array
        result_array_count = self.file_open_data(Alias1)
        result_array += result_array_count
        result_array = sorted(result_array, key=lambda x: x['"DATA_TANCAMENT"'])
        final_array = []
        for x in result_array:
            x.pop('"DATA_TANCAMENT"')
            final_array.append(x)
        last_month = datetime.strptime(self.newest_date_limit, '%d/%m/%y %H:%M:%S').month
        first_month = datetime.strptime(self.oldest_date_limit, '%d/%m/%y %H:%M:%S').month
        if self.to_validate is True and \
           self.check_view(first_month=first_month, last_month=last_month, year=self.year) is False:
            id = OpenDataModel.objects.filter(validated=True).aggregate(Max('id'))
            id = id.get('id__max')
            id = (page * 1000) if not id else (id + (page * 1000))
            self.create_records(self.add_id_opendata(copy.deepcopy(result_array), id),
                                create=self.create, validated=False)
        self.logger.info('Finished opendata queryset')
        return final_array

    def file_fitxer_fitxes_count(self):
        record_state_list = [0, 1, 2]
        record_state_id_list = [4, 7]
        details = ElementDetail.all_objects.filter(allows_open_data=True)
        request = Request.objects.filter(applicant_type_id__in=record_state_list)
        record_cards = RecordCard.objects.filter(
            (Q(element_detail_id__in=Subquery(details.values('id')))) &
            Q(record_state_id__in=record_state_id_list) &
            (Q(applicant_type_id__in=record_state_list) | Q(applicant_type_id=23) &
             Q(request_id__in=Subquery(request.values('id')))) &
            (~Q(support_id__in=[14, 20]) | (Q(support_id__in=[14, 20]) &
                                            Q(applicant_type_id__in=record_state_list))) &
            ~Q(support_id=8) &
            (Q(created_at__gte=datetime.strptime(self.limit_creating_at_date, '%d/%m/%y %H:%M:%S')) &
             (Q(closing_date__gte=datetime.strptime(self.oldest_date_limit, '%d/%m/%y %H:%M:%S'))) &
             (Q(closing_date__lte=datetime.strptime(self.newest_date_limit, '%d/%m/%y %H:%M:%S'))))
        )
        return record_cards.count()

    def query_count(self, page):
        def_page = str(page * 1000).replace(';', '')
        created_at_gte = str(datetime.strptime(self.limit_creating_at_date, '%d/%m/%y %H:%M:%S')).replace(';', '')
        closing_date_gte = str(datetime.strptime(self.oldest_date_limit, '%d/%m/%y %H:%M:%S')).replace(';', '')
        closing_date_lte = str(datetime.strptime(self.newest_date_limit, '%d/%m/%y %H:%M:%S')).replace(';', '')
        params = [created_at_gte, closing_date_gte, closing_date_lte, def_page]
        query = """select f1.created_at at time zone 'Europe/Madrid' as created_at,
            f1.closing_date at time zone 'Europe/Madrid' as closing_date,
            f1.* from record_cards_recordcard f1
            inner join themes_elementdetail f2 on f2.id=f1.element_detail_id
            inner join themes_element f3 on f3.id=f2.element_id
            inner join themes_area f4 on f4.id=f3.area_id
            left join record_cards_ubication f5 on f5.id=f1.ubication_id
            left join record_cards_recordcardresponse f6 on f6.record_card_id=f1.id
            inner join record_cards_request f7 on f7.id=f1.request_id
            left join record_cards_applicant f8 on f8.id=f7.applicant_id
            where f2.allows_open_data=True
              and f7.applicant_type_id in (0, 1, 2)
              and (f1.record_state_id in (4, 7))
              and (f1.applicant_type_id in (0, 1, 2) or f1.applicant_type_id=23)
              and (f1.support_id not in (14, 20) or (f1.support_id in (14, 20) and f1.applicant_type_id in (0, 1, 2)))
              and f1.support_id not in (8)
              and f1.created_at at time zone 'Europe/Madrid' > %s
              and f1.closing_date at time zone 'Europe/Madrid' > %s
              and f1.closing_date at time zone 'Europe/Madrid' < %s
              order by f1.id
                limit 1000 offset %s
            """
        return RecordCard.objects.raw(query, params)
