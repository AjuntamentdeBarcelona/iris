# Generated by Django 2.1.1 on 2019-06-03 07:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0019_auto_20190603_0923'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='enabled',
        ),
    ]
