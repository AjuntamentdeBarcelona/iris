# Generated by Django 2.1.1 on 2019-04-09 12:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0033_recordcardblock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ubication',
            name='district',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='iris_masters.District', verbose_name='District'),
        ),
    ]
