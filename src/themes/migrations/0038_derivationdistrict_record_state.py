# Generated by Django 2.1.1 on 2019-05-22 12:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0035_auto_20190508_1148'),
        ('themes', '0037_auto_20190513_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='derivationdistrict',
            name='record_state',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to='iris_masters.RecordState', verbose_name='Record State'),
        ),
    ]
