# Generated by Django 2.1.1 on 2021-04-14 07:53

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.mixins
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0018_auto_20210129_0958'),
        ('record_cards', '0127_auto_20210322_1707'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordCardFeaturesAux',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('value', models.CharField(blank=True, max_length=200, verbose_name='Value')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='Enabled')),
                ('is_theme_feature', models.BooleanField(db_index=True, default=True, help_text='Shows if the related feature is from the current record theme', verbose_name='Is theme feature')),
                ('feature', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='features.Feature', verbose_name='Feature')),
                ('record_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='record_cards.RecordCard', verbose_name='RecordCard')),
            ],
            options={
                'abstract': False,
            },
            bases=(iris_masters.mixins.CleanEnabledBase, models.Model),
        ),
        migrations.CreateModel(
            name='RecordCardSpecialFeaturesAux',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('value', models.CharField(blank=True, max_length=200, verbose_name='Value')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='Enabled')),
                ('is_theme_feature', models.BooleanField(db_index=True, default=True, help_text='Shows if the related feature is from the current record theme', verbose_name='Is theme feature')),
                ('feature', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='features.Feature', verbose_name='Feature')),
                ('record_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='record_cards.RecordCard', verbose_name='RecordCard')),
            ],
            options={
                'abstract': False,
            },
            bases=(iris_masters.mixins.CleanEnabledBase, models.Model),
        ),
    ]
