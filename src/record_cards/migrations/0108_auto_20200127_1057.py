# Generated by Django 2.1.1 on 2020-01-27 09:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0107_auto_20200127_1035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicant',
            name='enabled',
        ),
        migrations.RemoveField(
            model_name='citizen',
            name='enabled',
        ),
        migrations.RemoveField(
            model_name='socialentity',
            name='enabled',
        ),
    ]