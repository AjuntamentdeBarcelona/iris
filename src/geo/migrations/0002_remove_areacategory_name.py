# Generated by Django 2.2 on 2021-12-15 09:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='areacategory',
            name='name',
        ),
    ]