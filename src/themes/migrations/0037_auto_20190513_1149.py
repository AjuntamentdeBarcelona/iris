# Generated by Django 2.1.1 on 2019-05-13 09:49

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0035_auto_20190508_1148'),
        ('profiles', '0017_auto_20190508_1143'),
        ('themes', '0036_auto_20190513_1148'),
    ]

    operations = [
        migrations.CreateModel(
            name='DerivationDirect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='Enabled')),
                ('derivation_type', models.CharField(blank=True, max_length=3, verbose_name='Derivation Type')),
                ('element_detail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='themes.ElementDetail', verbose_name='Element Detail')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.Group', verbose_name='Group')),
                ('record_state', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='iris_masters.RecordState', verbose_name='Record State')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='derivationdirect',
            unique_together={('element_detail', 'record_state', 'group', 'enabled')},
        ),
    ]
