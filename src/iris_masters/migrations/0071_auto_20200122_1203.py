# Generated by Django 2.1.1 on 2020-01-22 11:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0070_auto_20200110_1610'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicanttype',
            name='description_ca',
        ),
        migrations.RemoveField(
            model_name='applicanttype',
            name='description_en',
        ),
        migrations.RemoveField(
            model_name='applicanttype',
            name='description_es',
        ),
        migrations.RemoveField(
            model_name='reason',
            name='description_ca',
        ),
        migrations.RemoveField(
            model_name='reason',
            name='description_en',
        ),
        migrations.RemoveField(
            model_name='reason',
            name='description_es',
        ),
        migrations.RemoveField(
            model_name='resolutiontype',
            name='description_ca',
        ),
        migrations.RemoveField(
            model_name='resolutiontype',
            name='description_en',
        ),
        migrations.RemoveField(
            model_name='resolutiontype',
            name='description_es',
        ),
    ]