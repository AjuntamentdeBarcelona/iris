# Generated by Django 2.2 on 2021-11-22 13:41

from django.db import migrations
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0015_auto_20210525_1548'),
    ]

    operations = [
        migrations.AlterField(
            model_name='batchfile',
            name='validated_by',
            field=iris_masters.models.UserIdField(blank=True, default='', max_length=36, verbose_name='User ID'),
        ),
    ]