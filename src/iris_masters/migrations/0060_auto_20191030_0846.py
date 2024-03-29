# Generated by Django 2.1.1 on 2019-10-30 07:46

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0059_auto_20191002_0822'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='announcement',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='applicanttype',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='inputchannel',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='reason',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='resolutiontype',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='responsetype',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='support',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
