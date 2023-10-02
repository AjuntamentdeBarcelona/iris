# Generated by Django 2.1.1 on 2019-03-18 11:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0029_auto_20190314_1600'),
        ('iris_masters', '0029_resolutiontype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordcardresolution',
            name='resolution_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='iris_masters.ResolutionType', verbose_name='Resolution Type'),
        ),
    ]