from rest_framework import serializers

from integrations.manual_task_schedule.models import ManualScheduleLog


class ManualScheduleLogSerializer(serializers.ModelSerializer):
    can_delete = serializers.BooleanField(source='can_be_deleted', read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = ManualScheduleLog
        fields = ['id', 'task', 'created_by', 'status_display', 'status', 'scheduled_date', 'cancelled_by',
                  'can_delete']
        read_only_fields = ['created_by', 'status_display', 'status', 'cancelled_by', 'id', 'can_delete']

    def get_status_display(self, obj):
        return obj.get_status_display()
