# Generated by Django 2.1.1 on 2019-10-30 07:46

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0011_auto_20190913_1620'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='feature',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='values',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='valuestype',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
