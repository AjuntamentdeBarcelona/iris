# Generated by Django 2.2 on 2021-11-22 13:41

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0018_auto_20210129_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=36, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='values',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=36, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='valuestype',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=36, verbose_name='User ID'),
        ),
    ]
