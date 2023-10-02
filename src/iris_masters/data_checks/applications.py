from iris_masters.models import Application


def check_required_applications(sender, **kwargs):
    applications = [
        {"id": Application.IRIS_PK, "description": "IRIS", "description_ca": "IRIS",
         "description_hash": Application.IRIS_HASH},
        {"id": Application.WEB_PK, "description": "WEB", "description_ca": "WEB",
         "description_hash": Application.WEB_HASH},
    ]

    for app in applications:
        application, _ = Application.objects.get_or_create(id=app["id"], defaults={
            "description": app["description"],
            "description_hash": app["description_hash"]
        })
        if app["description_hash"]:
            application.description_hash = app["description_hash"]
        application.save()
