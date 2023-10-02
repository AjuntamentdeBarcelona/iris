# Generated by Django 2.1.1 on 2019-11-11 16:43

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0061_applicanttype_send_response'),
        ('record_cards', '0081_monthindicator'),
    ]

    operations = [
        migrations.CreateModel(
            name='InternalOperator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.DateTimeField(editable=False, null=True)),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('document', models.CharField(db_index=True, max_length=15, unique=True, verbose_name='Internal operator document')),
                ('applicant_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='iris_masters.ApplicantType', verbose_name='Applicant Type')),
                ('input_channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='iris_masters.InputChannel', verbose_name='Input Channel')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]