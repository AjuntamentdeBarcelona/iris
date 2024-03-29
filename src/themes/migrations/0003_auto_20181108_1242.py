# Generated by Django 2.1.1 on 2018-11-08 11:42

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0002_auto_20181108_1025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='area',
            name='area_code',
            field=models.CharField(max_length=12, unique=True, verbose_name='Area Code'),
        ),
        migrations.AlterField(
            model_name='area',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='element',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='app_description',
            field=models.CharField(blank=True, default='', help_text='Description shown on APP', max_length=80),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='app_resolution_radius_meters',
            field=models.PositiveIntegerField(help_text='Maximum distance starting from the record card ubication, expressed in meters, in which an operator can resolve the task using the IRIS smartphone app.', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='applications',
            field=models.ManyToManyField(blank=True, through='themes.ElementDetailApplication', to='iris_masters.ExternalApplication'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='description',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='description_ca',
            field=models.TextField(default='', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='description_en',
            field=models.TextField(default='', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='description_es',
            field=models.TextField(default='', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='email_template',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='email_template_ca',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='email_template_en',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='email_template_es',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='external_protocol_id',
            field=models.CharField(blank=True, default='', help_text='Itaca ID for the desired protocol.', max_length=48, verbose_name='Protocol ID'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='features',
            field=models.ManyToManyField(blank=True, through='themes.ElementDetailFeature', to='features.Feature'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text',
            field=models.TextField(default='', verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text_ca',
            field=models.TextField(default='', null=True, verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text_en',
            field=models.TextField(default='', null=True, verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text_es',
            field=models.TextField(default='', null=True, verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text',
            field=models.TextField(default='', verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text_ca',
            field=models.TextField(default='', null=True, verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text_en',
            field=models.TextField(default='', null=True, verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text_es',
            field=models.TextField(default='', null=True, verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links',
            field=models.TextField(default='', verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links_ca',
            field=models.TextField(default='', null=True, verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links_en',
            field=models.TextField(default='', null=True, verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links_es',
            field=models.TextField(default='', null=True, verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd',
            field=models.TextField(default='', verbose_name='LOPD'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd_ca',
            field=models.TextField(default='', null=True, verbose_name='LOPD'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd_en',
            field=models.TextField(default='', null=True, verbose_name='LOPD'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd_es',
            field=models.TextField(default='', null=True, verbose_name='LOPD'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='pda_description',
            field=models.CharField(blank=True, default='', help_text='Description shown on PDA', max_length=80),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='rat_code',
            field=models.CharField(blank=True, default='', max_length=90),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='record_type',
            field=models.ForeignKey(help_text='Limit this detail to records of this type.', null=True, on_delete=django.db.models.deletion.PROTECT, to='iris_masters.RecordType', verbose_name='Record type'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='response_channels',
            field=models.ManyToManyField(blank=True, to='iris_masters.ResponseChannel'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='short_description',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='short_description_ca',
            field=models.CharField(blank=True, default='', max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='short_description_en',
            field=models.CharField(blank=True, default='', max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='short_description_es',
            field=models.CharField(blank=True, default='', max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='similarity_hours',
            field=models.PositiveSmallIntegerField(help_text='Maximum time, expressed in hours, between the creation time of two record cards for considering them similar', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='similarity_meters',
            field=models.PositiveIntegerField(help_text='Maximum distance, expressed in meters, between the ubications of two record cards for considering them similar.', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='sla_hours',
            field=models.PositiveSmallIntegerField(help_text='Maximum hours in which the town council commits to resolve an issues belonging this theme.', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='sms_template',
            field=models.CharField(blank=True, default='', max_length=480),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='sms_template_ca',
            field=models.CharField(blank=True, default='', max_length=480, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='sms_template_en',
            field=models.CharField(blank=True, default='', max_length=480, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='sms_template_es',
            field=models.CharField(blank=True, default='', max_length=480, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='validation_place_days',
            field=models.PositiveSmallIntegerField(help_text='Max number of days for validating a record card, modify the theme or reassign outside its environment.', null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='visibility',
            field=iris_masters.models.VisibilityOptionField(choices=[('p', 'Visible for all the profiles'), ('r', "Visible for the profiles responsible for the theme's area"), ('c', "Visible for the profiles responsible for the theme's area and a set of profiles for a concrete areas")], default='p', max_length=1, verbose_name='Visibility options'),
        ),
    ]
