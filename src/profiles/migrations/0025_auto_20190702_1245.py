# Generated by Django 2.1.1 on 2019-07-02 10:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0024_auto_20190701_1600'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='profiles',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='permissions',
        ),
    ]