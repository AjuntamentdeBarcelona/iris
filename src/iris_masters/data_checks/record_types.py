from iris_masters.models import RecordType


def check_required_record_types(sender, **kwargs):
    rtypes = [
        {"id": 1, "description": "Queja"},
        {"id": 2, "description": "Sugerencia"},
        {"id": 3, "description": "Incidencia"},
        {"id": RecordType.SERVICE_REQUEST, "description": "Petición de servicio"},
        {"id": RecordType.QUERY, "description": "Consulta"},
        {"id": 6, "description": "Agradecimiento"},
    ]

    for rtype in rtypes:
        RecordType.objects.get_or_create(id=rtype["id"], defaults={
            "description": rtype["description"],
            "tri": 0,
            "trt": 0,
        })
