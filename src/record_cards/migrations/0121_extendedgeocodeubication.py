# Generated by Django 2.1.1 on 2020-10-27 15:12

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0119_auto_20200414_1313'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtendedGeocodeUbication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('llepost_f', models.CharField(blank=True, max_length=3, verbose_name='Letter post f')),
                ('numpost_f', models.CharField(blank=True, max_length=60, verbose_name='Num post f')),
                ('dist_post', models.CharField(blank=True, max_length=60, verbose_name='Dist post')),
                ('codi_illa', models.CharField(blank=True, max_length=60, verbose_name='Codi illa')),
                ('solar', models.CharField(blank=True, max_length=60, verbose_name='Solar')),
                ('codi_parc', models.CharField(blank=True, max_length=60, verbose_name='Codi parc')),
                ('ubication', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='record_cards.Ubication', verbose_name='Ubication')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]