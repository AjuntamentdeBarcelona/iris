from profiles.models import Group


def set_group_plates(sender, **kwargs):
    Group.objects.rebuild()
    for group in Group.objects.filter(deleted__isnull=True).exclude(pk=0):
        group.group_plate = group.calculate_group_plate()
        group.save()
