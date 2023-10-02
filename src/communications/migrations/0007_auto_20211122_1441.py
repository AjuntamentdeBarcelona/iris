# Generated by Django 2.2 on 2021-11-22 13:41

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0006_conversation_require_answer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=36, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='conversationgroup',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=36, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='message',
            name='user_id',
            field=iris_masters.models.UserIdField(max_length=36, verbose_name='User ID'),
        ),
    ]