import logging

from django.db import IntegrityError

from iris_masters.models import Parameter
from iris_templates.template_params import TEMPLATE_PARAMS, get_parameter_key

logger = logging.getLogger(__name__)


def migrate_old_params():
    """
    Renames old translated param names for normalization.
    Old parameters are mapped in TEMPLATE_PARAMS.
    """
    logger.info('MIGRATE PARAMETERS | Normalizing translated Parameter names')
    for lang, params in TEMPLATE_PARAMS.items():
        logger.info('MIGRATE PARAMETERS | LANG: {LANG}')
        for base_name, translated_name in params.items():
            new_name = get_parameter_key(lang, base_name)
            try:
                if Parameter.objects.filter(parameter=translated_name).update(parameter=new_name):
                    logger.info(f'MIGRATE PARAMETERS | PARAM: {translated_name} | NEW NAME: {new_name}')
            except IntegrityError:
                logger.info(f'MIGRATE PARAMETERS | DUPLICATED PARAM: {new_name} exists | DELETE: {base_name}')
    logger.info('MIGRATE PARAMETERS | DONE')
