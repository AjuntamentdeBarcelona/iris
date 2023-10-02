# Generated by Django 2.2 on 2022-02-01 09:20

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0007_auto_20211122_1441'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=291, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='conversationgroup',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=291, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='message',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=291, verbose_name='User ID'),
        ),
    ]