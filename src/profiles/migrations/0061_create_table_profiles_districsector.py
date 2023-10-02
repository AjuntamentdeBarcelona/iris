
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0060_remove_group_pending_shipping_days'),
    ]

    operations = [
            migrations.RunSQL('CREATE TABLE public.profiles_districsector (dist_sect_id integer NOT NULL, description character varying(255) NOT NULL,  flag_ds integer NOT NULL,  discharge_date DATE NOT NULL,  user_id character varying(20) NOT NULL, fl_authorized integer NOT NULL,  list_description character varying(255) NOT NULL) ;'),
    ]