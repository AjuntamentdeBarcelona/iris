# Generated by Django 2.1.1 on 2019-03-26 10:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_auto_20190326_1141'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationprofile',
            old_name='profile',
            new_name='group',
        ),
    ]
