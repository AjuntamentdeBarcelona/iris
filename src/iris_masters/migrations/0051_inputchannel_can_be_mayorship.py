# Generated by Django 2.1.1 on 2019-09-03 07:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0050_auto_20190827_1749'),
    ]

    operations = [
        migrations.AddField(
            model_name='inputchannel',
            name='can_be_mayorship',
            field=models.BooleanField(default=False, help_text='Input Channel can be use to mayorship'),
        ),
    ]
