# Generated by Django 2.1.1 on 2019-10-30 16:44

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0042_auto_20191029_1652'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='profile',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
