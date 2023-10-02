from django.conf import settings
from django.db.models import Q
from django.utils import translation

from functools import reduce

from main.celery import app as celery_app
from themes.actions.theme_delete import ElementDetailDeleteAction


@celery_app.task(bind=True, queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def rebuild_theme_tree(*args, **kwargs):
    """
    :todo Pass language in parameters
    :param args:
    :param kwargs:
    :return:
    """
    old_lang = translation.get_language()
    translation.activate(settings.LANGUAGE_CODE)
    from themes.actions.theme_tree import ThemeTreeBuilder
    ThemeTreeBuilder().rebuild()
    translation.activate(old_lang)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def register_theme_ambits(element_detail_pk):
    """
    Task to register theme ambits
    :return:
    """
    from themes.models import ElementDetail
    element_detail = ElementDetail.objects.get(pk=element_detail_pk)
    element_detail.register_theme_ambit()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def set_themes_ambits():
    """
    Task to delay register_theme_task for every ElementDetail
    :return:
    """
    from themes.actions.theme_set_ambits import ThemeSetAmbits
    ThemeSetAmbits().set_theme_ambits()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def themes_average_close_days():
    """
    Task to calculate thmes average close days
    :return:
    """
    # get ThemeAverageCloseDays class and execute function calculate_average_close_days
    return


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def elementdetail_delete_action_execute(delete_register_pk):
    """
    Task to execute the element detail delete actions

    :param delete_register_pk: element detail delete register in
    :return:
    """
    from themes.models import ElementDetailDeleteRegister
    delete_register = ElementDetailDeleteRegister.objects.get(pk=delete_register_pk)
    delete_action = ElementDetailDeleteAction(delete_register)
    delete_action.elementdetail_postdelete_process()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def check_failed_elementdetail_delete_registers():
    from themes.models import ElementDetailDeleteRegister
    failed_registers = ElementDetailDeleteRegister.objects.filter(process_finished=False)
    for failed_delete_register in failed_registers:
        elementdetail_delete_action_execute.delay(failed_delete_register.pk)


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def set_response_channel_none_to_themes():
    from themes.models import ElementDetailResponseChannel, ElementDetail
    from iris_masters.models import Application, ResponseChannel

    details_ids = set(ElementDetail.objects.filter(
        **ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS).values_list("id", flat=True))

    details_respchannels_query = reduce(lambda previous, x: previous | Q(elementdetail_id=x,
                                                                         responsechannel_id=ResponseChannel.NONE,
                                                                         application_id=Application.IRIS_PK,
                                                                         enabled=True),
                                        details_ids, Q())
    existing_details = ElementDetailResponseChannel.objects.filter(
        details_respchannels_query).values_list("elementdetail_id", flat=True)

    details_to_create = {detail_id for detail_id in details_ids if detail_id not in existing_details}

    details_respchannels_to_create = [
        ElementDetailResponseChannel(
            elementdetail_id=detail_id, responsechannel_id=ResponseChannel.NONE, application_id=Application.IRIS_PK)
        for detail_id in details_to_create
    ]

    ElementDetailResponseChannel.objects.bulk_create(details_respchannels_to_create, batch_size=1000)
