# Generated by Django 2.1.1 on 2020-01-17 10:15

from django.db import migrations, models
import django.utils.timezone
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('protocols', '0006_auto_20190705_1259'),
    ]

    operations = [
        migrations.AddField(
            model_name='protocols',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Creation date'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='protocols',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='protocols',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AddField(
            model_name='protocols',
            name='user_id',
            field=iris_masters.models.UserIdField(default='IRIS', max_length=20, verbose_name='User ID'),
            preserve_default=False,
        ),
    ]