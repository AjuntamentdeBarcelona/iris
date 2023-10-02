from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0129_recordcardfeaturesaux_recordcardspecialfeaturesaux'),
    ]

    operations = [
            migrations.RunSQL('CREATE OR REPLACE FUNCTION ordre_cursor() RETURNS TABLE(ordre bigint, fecha_modificacion timestamp with time zone, record_card int) AS $func$ DECLARE record_card int; BEGIN FOR record_card IN SELECT record_card_id FROM record_cards_recordcardreasignation  LOOP RETURN QUERY SELECT ROW_NUMBER () OVER (ORDER BY created_at), updated_at, record_card_id FROM   record_cards_recordcardreasignation WHERE  record_card_id = record_card; END LOOP;  RETURN;  END;  $func$ LANGUAGE plpgsql;'),
    ]