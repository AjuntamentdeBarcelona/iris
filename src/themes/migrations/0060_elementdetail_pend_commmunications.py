# Generated by Django 2.1.1 on 2020-01-27 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0059_auto_20200124_1037'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementdetail',
            name='pend_commmunications',
            field=models.BooleanField(default=True, help_text='Send reminder of pending notifications on communications', verbose_name='Pending communications notifications'),
        ),
    ]
