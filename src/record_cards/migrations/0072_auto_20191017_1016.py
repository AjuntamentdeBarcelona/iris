# Generated by Django 2.1.1 on 2019-10-17 08:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0071_auto_20191015_1614'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recordcard',
            old_name='cancel_department',
            new_name='close_department',
        ),
    ]