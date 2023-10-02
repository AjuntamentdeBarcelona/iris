# Generated by Django 2.1.1 on 2019-09-19 12:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0063_auto_20190910_1507'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordcard',
            name='ans_limit_date',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='ANS limit date'),
        ),
        migrations.AlterField(
            model_name='recordcard',
            name='urgent',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Urgent'),
        ),
    ]