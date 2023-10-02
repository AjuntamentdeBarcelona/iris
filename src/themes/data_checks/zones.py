from django.utils import timezone

from themes.models import Zone


def check_zones(sender, **kwargs):
    zones = [
        {"id": Zone.CARRCENT_PK, "description": "CARRCENT", "deleted": None, "codename": "CARRCENT"},
        {
            "id": Zone.SENYAL_VERTICAL_PK,
            "description": "Nou senyal vertical",
            "deleted": timezone.now(),
            "codename": "SENYAL_VERTICAL"
        },
    ]

    for zone in zones:
        db_zone, _ = Zone.objects.get_or_create(id=zone["id"], defaults={"description": zone["description"],
                                                                         "deleted": zone["deleted"],
                                                                         "codename": zone["codename"]})

        db_zone.save()
