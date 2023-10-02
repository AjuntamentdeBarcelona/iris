# Generated by Django 2.1.1 on 2019-03-05 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0026_auto_20190213_1226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='elementdetail',
            name='app_description',
            field=models.CharField(blank=True, default='', help_text='Description shown on APP', max_length=255),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='app_description_ca',
            field=models.CharField(blank=True, default='', help_text='Description shown on APP', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='app_description_en',
            field=models.CharField(blank=True, default='', help_text='Description shown on APP', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='app_description_es',
            field=models.CharField(blank=True, default='', help_text='Description shown on APP', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text',
            field=models.TextField(blank=True, default='', verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text_ca',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text_en',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='footer_text_es',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Footer text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text',
            field=models.TextField(blank=True, default='', verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text_ca',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text_en',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='head_text_es',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Head text'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links',
            field=models.TextField(blank=True, default='', verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links_ca',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links_en',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='links_es',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Links'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd',
            field=models.TextField(blank=True, default='', verbose_name='GDPR'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd_ca',
            field=models.TextField(blank=True, default='', null=True, verbose_name='GDPR'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd_en',
            field=models.TextField(blank=True, default='', null=True, verbose_name='GDPR'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='lopd_es',
            field=models.TextField(blank=True, default='', null=True, verbose_name='GDPR'),
        ),
    ]
