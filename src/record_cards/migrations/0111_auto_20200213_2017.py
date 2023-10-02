# Generated by Django 2.1.1 on 2020-02-13 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0110_recordcardtextresponse_avoid_send'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordchunkedfile',
            name='file_type',
            field=models.IntegerField(choices=[(0, 'From Record Creation'), (1, 'From Record Detail'), (2, 'From Record Communications'), (3, 'From Public Web'), (4, 'From Response')], default=0, verbose_name='File Type'),
        ),
        migrations.AlterField(
            model_name='recordfile',
            name='file_type',
            field=models.IntegerField(choices=[(0, 'From Record Creation'), (1, 'From Record Detail'), (2, 'From Record Communications'), (3, 'From Public Web'), (4, 'From Response')], default=0, verbose_name='File Type'),
        ),
    ]