import requests
from django.conf import settings
from django.utils.module_loading import import_string
import logging
import re

logger = logging.getLogger(__name__)

try:
    list_generator = import_string(settings.STREET_TYPE_MAP_GENERATOR)
    street_type_list = list_generator(settings.STREET_TYPE_TRANSLATION_LANGUAGE_CODE)
except ImportError:
    logger.info(f"Unable to locate the module {settings.STREET_TYPE_MAP_GENERATOR}, Nominatim default street types "
                f"will be used.")
    street_type_list = []

try:
    ignored_keys_generator = import_string(settings.IGNORED_KEYS_LIST_GENERATOR)
    ignored_keys_list = ignored_keys_generator()
except ImportError:
    logger.info(f"Unable to locate the module {settings.IGNORED_KEYS_LIST_GENERATOR}, no keys will be ignored.")
    ignored_keys_list = []


def geo_json_search(query, format="jsonv2", country_codes="ES"):
    """
    This function returns a queryset of ubications in json format.
    It takes a string query and returns a location with latitude and longitude.
    The query argument must be a string of the form:

        'q=<query>' or 'street=<housenumber> <streetname>'

    Don't mix parameters and query.
    """

    # Checks for %20 spaces and replaces them

    query.replace("%20", "+")

    # Request is a free-form query:
    if "q=" in query:
        request_url = ("https://nominatim.openstreetmap.org/"
                       f"search?{query}&"
                       f"format={format}&"
                       f"countrycodes={country_codes}&"
                       "addressdetails=1&"
                       )
    else:
        # Request is structured
        """
        Order in the request matters, first parameters in the query string
        are evaluated first: format > postalcode > city ...

        Settings parameters may be overriden inside query. For example, if:

                        query = 'postalcode=12345'

        Query parameter is placed at the end of the request to gain priority.
        In the example above, postalcode from query will prevail vs settings.POSTAL_CODE.
        """
        request_url = ("https://nominatim.openstreetmap.org/"
                       f"search?format={format}&"
                       f"postalcode={settings.POSTAL_CODE}&"
                       f"city={settings.CITY}&"
                       f"county={settings.COUNTY}&"
                       f"state={settings.STATE}&"
                       f"country={settings.COUNTRY}&"
                       "addressdetails=1&"
                       f"{query}")
    if settings.GEO_VIEWBOX:
        request_url += f'&viewbox={settings.GEO_VIEWBOX}'
    req_json = requests.get(request_url).json()
    translate_type_search(req_json, street_types=street_type_list)
    check_display_name_search(req_json)
    return check_duplicates(req_json)


def geo_json_reverse(query, format="jsonv2"):
    """
    This function returns a queryset of ubications in json format.
    It takes latitude and longitude and returns a matching location.

    The query argument must be a string of the form:

        'lat=<lat_value>&lon=<lon_value>'
    """

    # Checks for %20 spaces and replaces them
    query.replace("%20", "+")
    request_url = ("https://nominatim.openstreetmap.org/"
                   f"reverse?format={format}&"
                   "zoom=18&"
                   f"{query}")

    request_url17 = ("https://nominatim.openstreetmap.org/"
                     f"reverse?format={format}&"
                     "zoom=17&"
                     f"{query}")

    req_json = requests.get(request_url).json()
    if 'address' in req_json:
        if 'road' not in req_json['address']:
            req_json17 = requests.get(request_url17).json()
            if 'road' in req_json17['address']:
                req_json['address']['road'] = req_json17['address']['road']
            else:
                req_json['address']['road'] = list(req_json['address'].values())[0]

        check_display_name(req_json)
        return translate_type_reverse(req_json, street_types=street_type_list)

    return req_json


def translate_type_search(json_req, street_types=None):
    if not street_types:
        return json_req
    else:
        for i in range(len(json_req)):
            if 'road' in json_req[i]['address']:
                for street_type in street_types:
                    if re.search(street_type, json_req[i]['address']['road'], re.IGNORECASE):
                        json_req[i]['type'] = street_type
                        break
                json_req[i]['type'] = street_types[2]
            else:
                json_req[i]['type'] = street_types[2]
                json_req[i]['address']['road'] = list(json_req[i]['address'].values())[0]


def translate_type_reverse(json_req, street_types=None):
    if not street_types:
        return json_req
    else:
        if 'road' in json_req['address']:
            for street_type in street_types:
                if re.search(street_type, json_req['address']['road'], re.IGNORECASE):
                    json_req['type'] = street_type
                    return json_req
            json_req['type'] = street_types[2]
        else:
            json_req['type'] = street_types[2]
            json_req['address']['road'] = list(json_req['address'].values())[0]
    return json_req


def remove_keys(address_dict):
    for key in ignored_keys_list:
        address_dict.pop(key, None)


def check_display_name_search(json_req):
    for i in range(len(json_req)):
        check_display_name(json_req[i])


def check_display_name(json_req, max_len=120):
    if len(json_req['display_name']) > max_len:
        comma = ", "
        remove_keys(json_req['address'])
        new_display_name = f"{comma.join(f'{value}' for key, value in json_req['address'].items())}"
        if len(new_display_name) > max_len:
            json_req['display_name'] = json_req['address']['road']
        else:
            json_req['display_name'] = new_display_name


def check_duplicates(json_req):
    if len(json_req) > 1:
        delete_list = []
        keep_index = 0
        for i in range(1, len(json_req)):
            if json_req[i]['address']['road'] == json_req[keep_index]['address']['road']:
                if 'house_number' in json_req[i]['address'] and 'house_number' not in json_req[keep_index]['address']:
                    delete_list.append(keep_index)
                    keep_index = i
                else:
                    delete_list.append(i)
            else:
                delete_list.append(i)

        for i in sorted(delete_list, reverse=True):
            del json_req[i]

    return json_req
