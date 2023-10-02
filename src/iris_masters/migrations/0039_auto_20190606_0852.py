# Generated by Django 2.1.1 on 2019-06-06 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0038_auto_20190604_1553'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reason',
            name='id',
            field=models.CharField(choices=[('-3', '-3'), ('19', '19'), ('16', '16'), ('17', '17'), ('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('12', '12'), ('13', '13'), ('-2', '-2'), ('-1', '-1'), ('14', '14'), ('26', '26'), ('100', '100'), ('200', '200'), ('300', '300'), ('400', '400'), ('500', '500')], max_length=3, primary_key=True, serialize=False, unique=True, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='recordstate',
            name='id',
            field=models.PositiveIntegerField(choices=[(0, 'Pending to validate'), (1, 'In planning'), (2, 'In resolution'), (3, 'Pending answer'), (4, 'Closed'), (5, 'Cancelled'), (6, 'Not processed'), (7, 'External processing'), (8, 'External returned')], primary_key=True, serialize=False, unique=True, verbose_name='ID'),
        ),
    ]
