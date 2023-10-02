# Generated by Django 2.1.1 on 2019-07-22 10:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ariadna', '0005_auto_20190711_1514'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ariadnarecord',
            name='record_card',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='registers',
                                    to='record_cards.RecordCard'),
        ),
    ]