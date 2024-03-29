# Generated by Django 2.1.1 on 2019-03-08 09:11

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0022_district'),
        ('profiles', '0003_auto_20190213_1226'),
        ('themes', '0028_auto_20190307_1703'),
    ]

    operations = [
        migrations.CreateModel(
            name='DerivationDistrict',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='iris_masters.District', verbose_name='District')),
                ('element_detail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='themes.ElementDetail', verbose_name='Element Detail')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.Profile', verbose_name='Profile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='derivation',
            name='element_detail',
        ),
        migrations.RemoveField(
            model_name='districtderivation',
            name='derivation',
        ),
        migrations.RemoveField(
            model_name='districtderivation',
            name='to_profile',
        ),
        migrations.RemoveField(
            model_name='industrialstatederivation',
            name='derivation',
        ),
        migrations.RemoveField(
            model_name='industrialstatederivation',
            name='to_profile',
        ),
        migrations.RemoveField(
            model_name='profilederivation',
            name='derivation',
        ),
        migrations.RemoveField(
            model_name='profilederivation',
            name='to_profile',
        ),
        migrations.RemoveField(
            model_name='protocolderivation',
            name='derivation',
        ),
        migrations.RemoveField(
            model_name='protocolderivation',
            name='to_profile',
        ),
        migrations.DeleteModel(
            name='Derivation',
        ),
        migrations.DeleteModel(
            name='DistrictDerivation',
        ),
        migrations.DeleteModel(
            name='IndustrialStateDerivation',
        ),
        migrations.DeleteModel(
            name='ProfileDerivation',
        ),
        migrations.DeleteModel(
            name='ProtocolDerivation',
        ),
    ]
