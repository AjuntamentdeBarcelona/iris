from django.utils.module_loading import import_string
from django.conf import settings
import logging

from record_cards.record_actions.geocode import get_geocoder_services_class

logger = logging.getLogger(__name__)


def api_streets(variable=''):
    """
    NOT USED!
    """
    GcodServices = get_geocoder_services_class()
    result = GcodServices().streets(variable=variable)
    return result

