from iris_masters.models import District


def check_districts(sender, **kwargs):
    districts = [
        {"id": District.CIUTAT_VELLA, "name": u"Distrito 0", "allow_derivation": True},
    ]

    for district in districts:
        db_district, _ = District.objects.get_or_create(id=district["id"], defaults={"name": district["name"]})
        if not district["allow_derivation"]:
            db_district.allow_derivation = False
            db_district.save()
