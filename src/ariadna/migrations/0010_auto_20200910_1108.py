# Generated by Django 2.1.1 on 2020-09-10 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ariadna', '0009_auto_20200713_1139'),
    ]

    operations = [
        migrations.AddField(
            model_name='ariadna',
            name='contact',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='contact'),
        ),
        migrations.AddField(
            model_name='ariadna',
            name='social_reason',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='social_reason'),
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='applicant_doc',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Applicant doc'),
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='applicant_doc_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'NIF'), (1, 'NIE'), (2, 'PASS')],
                                                   default=0, null=True, verbose_name='Document Type'),
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='applicant_name',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='Applicant name'),
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='applicant_surnames',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Applicant surnames'),
        ),
    ]