# Generated by Django 2.1.1 on 2020-01-23 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0103_auto_20200122_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='ubication',
            name='stair',
            field=models.CharField(blank=True, max_length=20, verbose_name='Stair'),
        ),
    ]