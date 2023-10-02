# Generated by Django 2.1.1 on 2020-02-25 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0073_auto_20200221_1523'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordstate',
            name='id',
            field=models.PositiveIntegerField(choices=[(0, 'Pending to be validated'), (1, 'Planned'), (2, 'In solution'), (3, 'Pending to give a reply'), (4, 'Closed'), (5, 'Canceled'), (6, 'Not processed'), (7, 'Externally processed'), (8, 'External returned')], primary_key=True, serialize=False, unique=True, verbose_name='ID'),
        ),
    ]
