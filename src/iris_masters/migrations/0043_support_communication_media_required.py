# Generated by Django 2.1.1 on 2019-07-08 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0042_auto_20190617_1617'),
    ]

    operations = [
        migrations.AddField(
            model_name='support',
            name='communication_media_required',
            field=models.BooleanField(default=False, verbose_name='Requires Communication Media'),
        ),
    ]
