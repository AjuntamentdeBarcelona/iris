# Generated by Django 2.2 on 2022-01-24 16:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0068_auto_20211215_1042'),
    ]

    operations = [
        migrations.RenameField(
            model_name='area',
            old_name='description_ca',
            new_name='description_gl',
        ),
        migrations.RenameField(
            model_name='element',
            old_name='alternative_text_ca',
            new_name='alternative_text_gl',
        ),
        migrations.RenameField(
            model_name='element',
            old_name='description_ca',
            new_name='description_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='app_description_ca',
            new_name='app_description_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='description_ca',
            new_name='description_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='email_template_ca',
            new_name='email_template_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='footer_text_ca',
            new_name='footer_text_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='head_text_ca',
            new_name='head_text_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='links_ca',
            new_name='links_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='lopd_ca',
            new_name='lopd_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='short_description_ca',
            new_name='short_description_gl',
        ),
        migrations.RenameField(
            model_name='elementdetail',
            old_name='sms_template_ca',
            new_name='sms_template_gl',
        ),
    ]