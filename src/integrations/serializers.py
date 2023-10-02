from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_celery_results.models import TaskResult
from rest_framework import serializers

from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, Serializer

from iris_masters.permissions import ADMIN
from record_cards.models import RecordCard
from record_cards.serializers import RecordCardSerializer
from .manual_task_schedule.models import task_allows_user_retry

from integrations.models import BatchFile


class RecordCardSenderSerializer(RecordCardSerializer):
    class Meta:
        model = RecordCard
        fields = ('id', 'user_id', 'created_at', 'description', 'normalized_record_id', 'closing_date',
                  'ans_limit_date', 'urgent', 'communication_media_detail', 'communication_media_date',
                  'support_numbers', 'element_detail_id', 'element_detail_id', 'request', 'request_id', 'ubication',
                  'record_state', 'record_state_id', 'record_type', 'applicant_type', 'communication_media', 'support',
                  'input_channel', 'features', 'special_features',)


TASK_DISPLAY = {
    'send_mail': _('Email send'),
    'themes_average_close_days': _('Calculate average close days for theme'),
    'calculate_last_month_indicators': _('Calculate last month indicators'),
    'generate_open_data_report': _('Generate Open Data report'),
    'generate_mib_report_fitxes': _('Generate MIB report file'),
    'send_next_to_expire_notifications': _('Send next to expire group notification'),
    'send_pending_validate_notifications': _('Send pending validate group notification'),
    'send_records_pending_communications_notifications': _('Send pending communications group notification'),
    'check_failed_elementdetail_delete_registers': _('Check element detail record movement after deletion'),
    'check_failed_group_delete_registers': _('Check group record movement after deletion'),
    'delete_chuncked_files': _('Remove auxiliary file uploads'),
    'check_messages_response_time_expired': _('Set messages as expired'),
}


class TaskTypeSerializer(Serializer):
    """
    Serializes a list of task types.
    """
    task_name = SerializerMethodField()
    display_name = SerializerMethodField()
    description = SerializerMethodField()
    user_retry = SerializerMethodField()
    next_schedule = SerializerMethodField()
    default_plan = SerializerMethodField()

    CRON_TEXTS = {
        'month_of_year': _('Month/s {} of year'),
        'every_month_of_year': _('Every month of year'),
        'day_of_month': _('Day/s: {} of month'),
        'every_day_of_month': _('Every day of month'),
        'every_hour': _('Every hour'),
        'hour': _('hour: {}'),
        'minute': _('minute: {}'),
        'every_minute': _('Every minute'),
    }

    def get_task_name(self, obj):
        return obj['task']

    def get_display_name(self, obj):
        return obj['task'].split('.')[-1]

    def get_description(self, obj):
        return TASK_DISPLAY.get(self.get_display_name(obj))

    def get_user_retry(self, obj):
        return task_allows_user_retry(obj['schedule'])

    def get_next_schedule(self, obj):
        if task_allows_user_retry(obj['schedule']):
            cron = obj['crontab']
            now = timezone.now()
            next = cron.remaining_estimate(now) + now
            return serializers.DateTimeField().to_representation(next)
        return ""

    def get_default_plan(self, obj):
        if task_allows_user_retry(obj['schedule']):
            cron = obj['crontab']
            dims = ['month_of_year', 'day_of_month', 'hour', 'minute']
            return ', '.join([
                self.crondim_to_str(dim, getattr(cron, dim, {}), getattr(cron, f'_orig_{dim}', {})) for dim in dims
            ])
        return ""

    def crondim_to_str(self, dim, expanded, original):
        if original == '*':
            return str(self.CRON_TEXTS[f'every_{dim}'])
        return str(self.CRON_TEXTS[dim]).format(','.join([str(e) for e in expanded]))


class TaskResultSerializer(ModelSerializer):
    display_name = SerializerMethodField()
    description = SerializerMethodField()

    class Meta:
        model = TaskResult
        fields = '__all__'

    def get_display_name(self, obj):
        return obj.task_name.split('.')[-1]

    def get_description(self, obj):
        desc = TASK_DISPLAY.get(self.get_display_name(obj))
        return desc


class TaskRetrySerializer(Serializer):
    """
    Receives and validates a task retry request. Only tasks marked as user_retry are allowed.
    """
    task = serializers.ChoiceField(choices=[(t, d) for t, d in TASK_DISPLAY.items() if task_allows_user_retry(t)])

    class Meta:
        model = TaskResult
        fields = '__all__'

    def save(self, **kwargs):
        pass


class BatchFileSerializer(ModelSerializer):
    actions = SerializerMethodField()

    class Meta:
        model = BatchFile
        fields = '__all__'

    def get_actions(self, obj):
        if not obj.validated_at:
            return {
                'validate': {
                    "permission": ADMIN,
                    "action_method": "post",
                    "action_url": reverse('private_api:integrations:batch_validate', args=[obj.pk]),
                    "can_perform": True,
                }
            }
        return {}
