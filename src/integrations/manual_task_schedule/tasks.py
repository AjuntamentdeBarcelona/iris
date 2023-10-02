import json
import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string
from django.conf import settings
from django_celery_results.models import TaskResult

from celery import states as celery_states

from integrations.manual_task_schedule.models import ManualScheduleLog, get_tasks, get_user_manageable_tasks

from main.celery import app as celery_app


logger = logging.getLogger(__name__)


class InvalidTask(Exception):
    pass


def execute_task_from_schedule(task_import_path: str, schedule_log: ManualScheduleLog):
    task = import_string(task_import_path)
    task_kwargs = json.loads(schedule_log.json) if schedule_log.json else {}
    if not hasattr(task, 'delay'):
        raise InvalidTask(f'Received invalid task {task_import_path}, it should have a valid delay method.')
    return getattr(task, 'delay')(**task_kwargs)


def calc_countdown_for_task(manual_schedule: ManualScheduleLog):
    now = timezone.now()
    return (manual_schedule.scheduled_date - now).seconds if manual_schedule.scheduled_date > now else 0


@celery_app.task(max_retries=0, queue=settings.CELERY_LOW_QUEUE_NAME)
def launch_manual_scheduled_task(task_import_path: str, schedule_info_pk: int):
    """
    Given a ManualScheduleLog enqueues a valid call to a task that which import path is placed in the task_import_path.
    :param schedule_info_pk: ManualScheduleLog pk for retrieving the params
    :param task_import_path: Import path for the task
    """
    try:
        schedule_log = ManualScheduleLog.objects.filter(status=ManualScheduleLog.SCHEDULED).get(pk=schedule_info_pk)
        execute_task_from_schedule(task_import_path, schedule_log)
        schedule_log.status = ManualScheduleLog.READY
        schedule_log.save()
        return schedule_log.status
    except ManualScheduleLog.DoesNotExist:
        logger.info('MANUAL TASK | CANCELLED')
    except ImportError:
        logger.error('MANUAL TASK | CANNOT IMPORT TASK')
    except InvalidTask as e:
        logger.error(f'MANUAL TASK | {e}')
    return False


def schedule_for(manual_schedule: ManualScheduleLog):
    countdown = calc_countdown_for_task(manual_schedule)
    launch_manual_scheduled_task.apply_async(kwargs={
        'task_import_path': manual_schedule.task,
        'schedule_info_pk': manual_schedule.pk,
    }, countdown=countdown)


@celery_app.task(bind=True, queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=1)
def remove_celery_results():
    """
    Test celery use
    :return:
    """
    tasks = get_tasks()
    user_tasks = get_user_manageable_tasks()
    now = timezone.now()
    non_user = [t for t in tasks if t not in user_tasks]
    logger.info("CELERY | TASK RESULTS CLEAN UP | START")

    TaskResult.objects.exclude(
        Q(task_name__in=tasks) | Q(status=celery_states.FAILURE)
    ).delete()
    logger.info("CELERY | TASK RESULTS CLEAN UP | CLEANED SUCCESS NON USER LOGGED LAST DAY RESULTS")

    last_month = now - timedelta(days=31)
    TaskResult.objects.filter(
        date_done__lte=last_month
    ).exclude(
        Q(task_name__in=non_user)
    ).delete()
    logger.info("CELERY | TASK RESULTS CLEAN UP | CLEANED NON USER MANAGEABLE LOGGED LAST MONTH RESULTS")

    last_year = now - timedelta(days=365)
    TaskResult.objects.filter(
        date_done__lte=last_year
    ).exclude(
        Q(task_name__in=user_tasks)
    ).delete()
    logger.info("CELERY | TASK RESULTS CLEAN UP | CLEANED USER MANAGEABLE TASK LAST YEAR RESULTS")
