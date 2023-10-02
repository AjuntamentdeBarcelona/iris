# Generated by Django 2.2 on 2021-12-02 14:17

from django.db import migrations, models
import drf_chunked_upload.models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0132_auto_20211122_1447'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordchunkedfile',
            name='file',
            field=models.FileField(max_length=255, null=True, upload_to=drf_chunked_upload.models.generate_filename),
        ),
    ]