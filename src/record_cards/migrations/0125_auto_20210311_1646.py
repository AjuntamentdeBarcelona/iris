# Generated by Django 2.1.1 on 2021-03-11 15:46

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0124_auto_20210305_1149'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordcardreasignation',
            name='user_id',
            field=iris_masters.models.UserIdField(db_index=True, max_length=20, verbose_name='User ID'),
        ),
        migrations.AlterField(
            model_name='recordcardstatehistory',
            name='user_id',
            field=iris_masters.models.UserIdField(db_index=True, max_length=20, verbose_name='User ID'),
        ),
    ]