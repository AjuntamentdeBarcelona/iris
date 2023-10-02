# Generated by Django 2.1.1 on 2019-05-07 13:22

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0034_auto_20190412_1159'),
        ('profiles', '0015_group_is_ambit'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupInputChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
                ('order', models.PositiveIntegerField(db_index=True, default=0)),
                ('update_user_id', iris_masters.models.UserIdField(blank=True, max_length=20, verbose_name='Update User ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='profiles.Group', verbose_name='Group')),
                ('input_channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='iris_masters.InputChannel', verbose_name='Input Channel')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='groupinputchannel',
            unique_together={('group', 'input_channel', 'enabled')},
        ),
    ]
