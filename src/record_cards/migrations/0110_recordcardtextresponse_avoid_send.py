# Generated by Django 2.1.1 on 2020-02-12 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0109_applicant_pend_anonymize'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordcardtextresponse',
            name='avoid_send',
            field=models.BooleanField(default=False, verbose_name='Avoid send answer'),
        ),
    ]
