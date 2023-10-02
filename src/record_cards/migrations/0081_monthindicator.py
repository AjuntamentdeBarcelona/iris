# Generated by Django 2.1.1 on 2019-11-08 15:51

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0043_auto_20191030_1744'),
        ('record_cards', '0080_auto_20191108_0935'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthIndicator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(verbose_name='Year')),
                ('month', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)], verbose_name='Month')),
                ('pending_validation', models.PositiveSmallIntegerField(verbose_name='Pending Validation')),
                ('processing', models.PositiveSmallIntegerField(verbose_name='Processing')),
                ('closed', models.PositiveSmallIntegerField(verbose_name='closed')),
                ('cancelled', models.PositiveSmallIntegerField(verbose_name='Cancelled')),
                ('external_processing', models.PositiveSmallIntegerField(verbose_name='External Processing')),
                ('pending_records', models.PositiveSmallIntegerField(verbose_name='Pending records')),
                ('average_close_days', models.PositiveSmallIntegerField(verbose_name='Average Close Days')),
                ('average_age_days', models.PositiveSmallIntegerField(verbose_name='Average Age Days')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='profiles.Group', verbose_name='Group')),
            ],
        ),
    ]
