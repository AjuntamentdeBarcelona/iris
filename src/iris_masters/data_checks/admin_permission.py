from django.core.exceptions import MultipleObjectsReturned

from profiles.models import Profile, ProfilePermissions, Permission


def check_admin_profile(sender, **kwargs):
    profile, created = Profile.objects.get_or_create(description='Admin')
    for perm in Permission.objects.all():
        try:
            ProfilePermissions.objects.get_or_create(profile=profile, permission=perm, enabled=True)
        except MultipleObjectsReturned:
            pass
