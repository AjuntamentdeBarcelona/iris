# Generated by Django 2.1.1 on 2019-03-05 11:01

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0022_district'),
        ('record_cards', '0024_auto_20190305_1012'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordCardStateHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('next_state', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='next', to='iris_masters.RecordState', verbose_name='RecordCard Next State')),
                ('previous_state', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='previous', to='iris_masters.RecordState', verbose_name='RecordCard Previous State')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='recordcard',
            name='appointment_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Appointment Time'),
        ),
        migrations.AddField(
            model_name='recordcardhistory',
            name='appointment_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Appointment Time'),
        ),
        migrations.AddField(
            model_name='recordcardstatehistory',
            name='record_card',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='record_cards.RecordCard', verbose_name='RecordCard'),
        ),
    ]
