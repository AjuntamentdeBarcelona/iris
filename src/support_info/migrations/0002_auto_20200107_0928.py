# Generated by Django 2.1.1 on 2020-01-07 08:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('support_info', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='supportinfo',
            options={'ordering': ('type', 'title')},
        ),
    ]
