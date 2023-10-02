from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):

    help = "List the permissions of every user"

    def handle(self, *args, **options):
        self.stdout.write('username, permission')
        for user in User.objects.all().select_related('usergroup'):
            if hasattr(user, 'usergroup'):
                permissions = user.usergroup.get_user_permissions()
                for permission in permissions:
                    self.stdout.write(f'{user.username}, {permission.codename}')
