# Generated by Django 2.1.1 on 2019-09-18 07:41

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0033_auto_20190912_0847'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='group',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
