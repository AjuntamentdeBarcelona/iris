import logging

from django.conf import settings

GROUP_HEADER_NOT_FOUND = 'NOT_FOUND'
CTRL_USER_NF = 'NOT_FOUND'
logger = logging.getLogger(__name__)


def get_user_groups_header_list(user_groups_header):
    logger.info('AUTH WITH GROUPS IN HEADER {}'.format(user_groups_header))
    if not user_groups_header:
        return []
    if user_groups_header == GROUP_HEADER_NOT_FOUND:
        return []
    app_groups = {key: value.split(';') for key, value in [app.split(':') for app in user_groups_header.split(',')]}
    logger.info('DETECTED APP GROUPS IN HEADER {}'.format(app_groups.get(settings.IRIS_CTRLUSER_APPNAME, [])))
    return app_groups.get(settings.IRIS_CTRLUSER_APPNAME, [])
