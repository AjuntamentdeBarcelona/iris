from django.core.management.base import BaseCommand

from themes.models import ApplicationElementDetail


class Command(BaseCommand):
    """
    Command to clean ApplicationElementDetail values tu allow uniquetogether constraint
    """

    help = "Clean ApplicationElementDetail"

    def handle(self, *args, **options):
        self.stdout.write('Start cleaning Application ElementDetail')

        application_element_details = ApplicationElementDetail.objects.all()
        for instance in application_element_details:
            query_params = {
                'detail_id': instance.detail_id,
                'application_id': instance.application_id,
                'enabled': instance.enabled
            }
            repeat_ids = ApplicationElementDetail.objects.filter(**query_params).values_list('pk', flat=True)
            if repeat_ids.count() > 1:
                ApplicationElementDetail.objects.filter(pk__in=repeat_ids).exclude(pk=repeat_ids.last()).delete()
                self.stdout.write('Delete repeated objects with: {}'.format(query_params))
            else:
                self.stdout.write('No duplicated objects with: {}'.format(query_params))
