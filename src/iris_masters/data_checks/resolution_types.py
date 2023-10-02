from iris_masters.models import ResolutionType


def check_resolution_types(sender, **kwargs):
    resolution_types = [
        {"id": 1, "description": "Resuelto", "user_id": "IRIS",
         "order": 1, "deleted": None, "can_claim_inside_ans": False},
        {"id": 2, "description": "No se hará ninguna actuación", "user_id": "IRIS",
         "order": 3, "deleted": None, "can_claim_inside_ans": False},
        {"id": ResolutionType.PROGRAM_ACTION, "description": "Es programa actuació", "user_id": "IRIS",
         "order": 2, "deleted": None, "can_claim_inside_ans": False},
    ]

    for resolution_type in resolution_types:
        db_resolution_type, _ = ResolutionType.all_objects.get_or_create(id=resolution_type["id"], defaults={
            "description": resolution_type["description"], "deleted": None, "order": resolution_type["order"],
            "user_id": resolution_type["user_id"], "can_claim_inside_ans": resolution_type["can_claim_inside_ans"]})
        if db_resolution_type.deleted:
            ResolutionType.all_objects.filter(pk=db_resolution_type.pk).update(deleted=None)
