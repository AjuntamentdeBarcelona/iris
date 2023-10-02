# Generated by Django 2.1.1 on 2020-02-18 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0111_auto_20200213_2017'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicantresponse',
            name='email',
            field=models.EmailField(blank=True, db_index=True, max_length=50, verbose_name='Email'),
        ),
        migrations.AlterField(
            model_name='applicantresponse',
            name='floor',
            field=models.CharField(blank=True, max_length=50, verbose_name='Floor'),
        ),
    ]