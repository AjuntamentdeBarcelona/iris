# Generated by Django 2.1.1 on 2019-09-12 06:47

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0032_auto_20190911_1044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='profile_ctrl_user_id',
            field=iris_masters.models.UserIdField(db_index=True, max_length=20, verbose_name='Profile ctrl user id'),
        ),
    ]
