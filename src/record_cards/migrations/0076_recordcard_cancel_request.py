# Generated by Django 2.1.1 on 2019-10-28 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0075_auto_20191021_1145'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordcard',
            name='cancel_request',
            field=models.BooleanField(default=False, verbose_name='Cancel Request'),
        ),
    ]
