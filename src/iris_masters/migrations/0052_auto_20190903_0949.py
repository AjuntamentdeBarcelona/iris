# Generated by Django 2.1.1 on 2019-09-03 07:49

from django.db import migrations


def set_mayorship_flag_inputchannel(apps, schema_editor):
    InputChannel = apps.get_model('iris_masters', 'InputChannel')
    gabinet_alcaldia_pk = 13  # mayorship input_channel pk
    mayorship_channel = InputChannel.objects.get(pk=gabinet_alcaldia_pk)
    mayorship_channel.can_be_mayorship = True
    mayorship_channel.save()


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0051_inputchannel_can_be_mayorship'),
    ]

    operations = [
    ]
