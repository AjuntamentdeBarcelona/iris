# Generated by Django 2.1.1 on 2019-06-03 07:23

from django.db import migrations


def group_soft_delete(apps, schema_editor):
    Group = apps.get_model('profiles', 'Group')
    for group in Group.objects.all():
        if not group.enabled:
            group.deleted = group.created_at
            group.save()


def group_enabled(apps, schema_editor):
    Group = apps.get_model('profiles', 'Group')
    for group in Group.objects.all():
            group.enabled = False if group.deleted else True
            group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0018_group_deleted'),
    ]

    operations = [
        migrations.RunPython(group_soft_delete, group_enabled),
    ]
