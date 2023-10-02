from django.conf import settings
from django.utils import translation

from main.celery import app as celery_app
from profiles.group_delete import GroupDeleteAction
from profiles.actions.update_group_plates import UpdateGroupPlates
from profiles.models import GroupDeleteRegister, Group, Profile
from profiles.notifications import GroupNotifications
from django.utils.module_loading import import_string

try:
    set_default_admin = import_string(settings.SET_DEFAULT_ADMIN_BACKEND)
    set_group_plates = import_string(settings.SET_GROUP_PLATES_BACKEND)
    set_ambit_coordinators = import_string(settings.SET_AMBIT_COORDINATORS_BACKEND)
except ImportError as e:
    raise e


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def group_delete_action_execute(group_delete_register_pk):
    """
    Task to execute the group delete actions
    :return:
    """
    group_delete_register = GroupDeleteRegister.objects.get(pk=group_delete_register_pk)
    delete_action = GroupDeleteAction(group_delete_register)
    delete_action.group_delete_process()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def check_failed_group_delete_registers():
    failed_registers = GroupDeleteRegister.objects.filter(process_finished=False)
    for failed_delete_register in failed_registers:
        group_delete_action_execute.delay(failed_delete_register.pk)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_next_to_expire_notifications():
    translation.activate(settings.LANGUAGE_CODE)
    for group in Group.objects.filter(deleted__isnull=True):
        group_notifications = GroupNotifications(group)
        group_notifications.next_to_expire_notification()
    translation.deactivate()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_pending_validate_notifications():
    translation.activate(settings.LANGUAGE_CODE)
    for group in Group.objects.filter(deleted__isnull=True):
        group_notifications = GroupNotifications(group)
        group_notifications.pending_validate_notification()
    translation.deactivate()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_records_pending_communications_notifications():
    translation.activate(settings.LANGUAGE_CODE)
    for group in Group.objects.filter(deleted__isnull=True):
        group_notifications = GroupNotifications(group)
        group_notifications.records_pending_communications()
    translation.deactivate()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_allocated_notification(group_pk, record_card_pk):
    translation.activate(settings.LANGUAGE_CODE)
    group = Group.objects.get(pk=group_pk)
    from record_cards.models import RecordCard
    record_card = RecordCard.objects.get(pk=record_card_pk)
    GroupNotifications(group).records_allocation_notification(record_card)
    translation.deactivate()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def group_update_group_descendants_plates(group_pk):
    """
    Task to execute update the group plate and the plate of its descendants
    :return:
    """
    group = Group.objects.get(pk=group_pk)
    UpdateGroupPlates(group).update_group_descendants_plates()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def rebuild_tree():
    """
    Task to execute update the group plate and the plate of its descendants
    :return:
    """
    Group.objects.rebuild()
    for group in Group.objects.filter(deleted__isnull=True).exclude(pk=0):
        group.group_plate = group.calculate_group_plate()
        group.save()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def profile_post_delete(profile_pk):
    profile = Profile.all_objects.get(pk=profile_pk)
    profile.disable_profile_usages()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def profiles_data_checks():
    set_default_admin(None)
    set_group_plates(None)
    set_ambit_coordinators(None)
