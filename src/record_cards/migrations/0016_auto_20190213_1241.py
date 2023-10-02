# Generated by Django 2.1.1 on 2019-02-13 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0015_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='applicantresponse',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='applicantresponse',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='citizen',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='citizen',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='recordcard',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='recordcard',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='recordcardfeatures',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='recordcardfeatures',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='recordcardhistory',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='recordcardhistory',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='recordcardspecialfeatures',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='recordcardspecialfeatures',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='request',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='request',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='socialentity',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='socialentity',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='ubication',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='ubication',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
    ]
