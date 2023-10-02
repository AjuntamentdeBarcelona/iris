from django.core.management.base import BaseCommand

from themes.tasks import rebuild_theme_tree


class Command(BaseCommand):
    """
    Command to clean ApplicationElementDetail values tu allow uniquetogether constraint
    """
    help = "Clean ApplicationElementDetail"

    def handle(self, *args, **options):
        self.stdout.write('TREE_CACHE: Rebuilding theme tree cache')
        rebuild_theme_tree()
        self.stdout.write('TREE_CACHE: Theme tree cache built')
