# Generated by Django 2.2 on 2022-02-01 09:20

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0020_auto_20220124_1734'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=291, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='values',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=291, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='valuestype',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=291, verbose_name='User ID'),
        ),
    ]