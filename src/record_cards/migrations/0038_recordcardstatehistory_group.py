# Generated by Django 2.1.1 on 2019-04-10 11:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0009_auto_20190327_1710'),
        ('record_cards', '0037_auto_20190327_1710'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordcardstatehistory',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='profiles.Group', verbose_name='Group'),
        ),
    ]
