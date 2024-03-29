# Generated by Django 2.1.1 on 2020-03-06 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0115_recordcardhistory_creation_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordchunkedfile',
            name='file_type',
            field=models.IntegerField(choices=[(0, 'From Record Creation'), (1, 'From Record Detail'), (2, 'From Record Communications'), (3, 'From Public Web'), (4, 'From Response'), (5, 'IRIS1')], default=0, verbose_name='File Type'),
        ),
        migrations.AlterField(
            model_name='recordfile',
            name='file_type',
            field=models.IntegerField(choices=[(0, 'From Record Creation'), (1, 'From Record Detail'), (2, 'From Record Communications'), (3, 'From Public Web'), (4, 'From Response'), (5, 'IRIS1')], default=0, verbose_name='File Type'),
        ),
    ]
