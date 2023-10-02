# Generated by Django 2.1.1 on 2019-02-13 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0025_auto_20190206_0923'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationelementdetail',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='applicationelementdetail',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='area',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='area',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='element',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='element',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='elementdetailfeature',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='elementdetailfeature',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='keyword',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='keyword',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
        migrations.AlterField(
            model_name='themegroup',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='themegroup',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Last update'),
        ),
    ]
