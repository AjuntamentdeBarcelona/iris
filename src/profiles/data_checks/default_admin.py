from django.contrib.auth.models import User

from iris_masters.models import InputChannel
from profiles.models import Group, UserGroup, Profile, ProfileUserGroup, GroupsUserGroup, GroupReassignation, \
    GroupInputChannel

from django.conf import settings


def set_default_admin(sender, **kwargs):
    if settings.DEFAULT_ADMIN:
        admin, _ = User.objects.get_or_create(username=settings.DEFAULT_ADMIN)
        if settings.DEFAULT_ADMIN_PASSWORD:
            admin.set_password(settings.DEFAULT_ADMIN_PASSWORD)
            admin.active = True
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        try:
            coord, _ = Group.objects.get_or_create(level=0, is_anonymous=False, defaults={
                'description': 'COORDINADOR GENERAL',
                'profile_ctrl_user_id': 'C0',
                'citizen_nd': True,
                'is_anonymous': False,
                'is_ambit': True,
            })
            ugroup, _ = UserGroup.objects.get_or_create(user=admin, defaults={
                'group': coord
            })
            ugroup.group = coord
            ugroup.save()
            GroupsUserGroup.objects.get_or_create(group=coord, user_group=ugroup)
        except Group.MultipleObjectsReturned:
            pass


def create_basic_group_struct():
    try:
        root = Group.objects.get(level=0, is_anonymous=False)
        coord, _ = Group.objects.get_or_create(parent=root, is_anonymous=False, defaults={
            'description': 'COORDINADOR AREA',
            'profile_ctrl_user_id': 'C1',
            'citizen_nd': True,
            'is_anonymous': False,
            'is_ambit': True,
        })
        resp, _ = Group.objects.get_or_create(parent=coord, is_anonymous=False, defaults={
            'description': 'RESPONSABLE AREA',
            'profile_ctrl_user_id': 'R1',
            'citizen_nd': True,
            'is_anonymous': False,
            'is_ambit': True,
        })
        op, _ = Group.objects.get_or_create(parent=resp, is_anonymous=False, defaults={
            'description': 'COORDINADOR GENERAL',
            'profile_ctrl_user_id': 'R2',
            'citizen_nd': True,
            'is_anonymous': False,
            'is_ambit': True,
        })
        groups = [root, coord, resp, op]
        for g in groups:
            for other_g in groups:
                if other_g != g:
                    GroupReassignation.objects.create(origin_group=g, reasign_group=other_g)
            GroupInputChannel.objects.create(group=g, input_channel_id=InputChannel.IRIS)
    except Group.MultipleObjectsReturned:
        pass


def set_ambit_coordinators(sender, **kwargs):
    for group in Group.objects.filter(deleted__isnull=True).exclude(pk=0):
        group.ambit_coordinator = group.get_ambit_parent()
        group.save()

    if settings.DEFAULT_ADMIN:
        admin, _ = User.objects.get_or_create(username=settings.DEFAULT_ADMIN)
        group_ids = ['DAIR0000', 'CAEX0000', 'AMA0000', 'DNOU0000']
        groups = Group.objects.filter(profile_ctrl_user_id__in=group_ids)
        if groups.exists():
            ugroup, _ = UserGroup.objects.get_or_create(user=admin, defaults={'group': groups.first()})
            admin_prof, _ = Profile.objects.get_or_create(description='Admin')
            for group in groups:
                gp, _ = ProfileUserGroup.objects.get_or_create(user_group=ugroup, profile=admin_prof)
                gp.enabled = True
                gp.save()
                gug, _ = GroupsUserGroup.objects.get_or_create(user_group=ugroup, group=group)
                gug.enabled = True
                gug.save()
