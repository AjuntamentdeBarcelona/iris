from django.core.management.base import BaseCommand

from themes.models import ElementDetail


class Command(BaseCommand):
    """
    Command to clean ApplicationElementDetail values tu allow uniquetogether constraint
    """
    help = "Clean ApplicationElementDetail"

    def handle(self, *args, **options):
        self.stdout.write('TREE_CACHE: Rebuilding theme ambits')
        for detail in ElementDetail.objects.all():
            detail.register_theme_ambit()
        self.stdout.write('TREE_CACHE: theme ambits built')
