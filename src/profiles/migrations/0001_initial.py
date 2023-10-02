# Generated by Django 2.1.1 on 2019-01-11 14:06

from django.db import migrations, models
import iris_masters.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateField(auto_now=True, verbose_name='Last update')),
                ('description', models.CharField(max_length=40, unique=True, verbose_name='Description')),
                ('description_es', models.CharField(max_length=40, null=True, unique=True, verbose_name='Description')),
                ('description_ca', models.CharField(max_length=40, null=True, unique=True, verbose_name='Description')),
                ('description_en', models.CharField(max_length=40, null=True, unique=True, verbose_name='Description')),
                ('profile_hierarchical', models.PositiveIntegerField(default=0, verbose_name='Profile Hierarchical')),
                ('profile_ctrl_user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='Profile ctrl user id')),
                ('dist_sect_id', models.PositiveIntegerField(default=0, verbose_name='Dist sect id')),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
                ('service_line', models.PositiveIntegerField(default=0, verbose_name='Service line')),
                ('sector', models.PositiveIntegerField(default=0, verbose_name='Sector')),
                ('no_reasigned', models.BooleanField(default=True, verbose_name='No Reasigned')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('signature', models.URLField(verbose_name='Signature')),
                ('icon', models.URLField(verbose_name='Icon')),
                ('letter_template_id', models.PositiveIntegerField(default=0, verbose_name='Letter template id')),
                ('pending_shipping_days', models.PositiveIntegerField(default=0, verbose_name='Pending shipping days')),
                ('last_pending_delivery', models.DateField(verbose_name='Last pending delivery')),
                ('citizen_nd', models.BooleanField(default=True, verbose_name='Citizen ND')),
                ('certificate', models.BooleanField(default=True, verbose_name='Certificate')),
                ('super_sector', models.PositiveIntegerField(default=0, verbose_name='Super Sector')),
                ('validate_thematic_tree', models.BooleanField(default=True, verbose_name='Vlidate Thematic Tree')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]