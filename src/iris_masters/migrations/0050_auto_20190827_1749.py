# Generated by Django 2.1.1 on 2019-08-27 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0049_auto_20190826_1643'),
    ]

    operations = [
        migrations.AddField(
            model_name='resolutiontype',
            name='description_ca',
            field=models.CharField(max_length=40, null=True, unique=True, verbose_name='Description'),
        ),
        migrations.AddField(
            model_name='resolutiontype',
            name='description_en',
            field=models.CharField(max_length=40, null=True, unique=True, verbose_name='Description'),
        ),
        migrations.AddField(
            model_name='resolutiontype',
            name='description_es',
            field=models.CharField(max_length=40, null=True, unique=True, verbose_name='Description'),
        ),
    ]
