from iris_masters.models import ApplicantType, InputChannelApplicantType, InputChannel


def check_applicant_types(sender, **kwargs):
    applicant_types = [
        {"id": ApplicantType.CIUTADA, "description": "CIUDADANO", "deleted": None, "order": 1, "user_id": "1"},
        {"id": ApplicantType.COLECTIUS, "description": "COLECTIVOS", "deleted": None, "order": 5, "user_id": "1"},
        {"id": ApplicantType.RECLAMACIO_INTERNA, "description": "RECLAMACIÓN INTERNA", "deleted": None, "order": 19,
         "user_id": "IRIS"},
        {"id": ApplicantType.OPERADOR, "description": "OPERADOR IRIS", "deleted": None, "order": 19,
         "user_id": "IRIS"},
    ]

    for applicant_type in applicant_types:
        _, _ = ApplicantType.objects.get_or_create(id=applicant_type["id"], defaults={
            "description": applicant_type["description"], "deleted": applicant_type["deleted"],
            "order": applicant_type["order"], "user_id": applicant_type["user_id"]})

    InputChannelApplicantType.objects.get_or_create(
        applicant_type_id=ApplicantType.RECLAMACIO_INTERNA,
        input_channel_id=InputChannel.RECLAMACIO_INTERNA,
        enabled=True,
    )
    InputChannelApplicantType.objects.get_or_create(
        applicant_type_id=ApplicantType.CIUTADA,
        input_channel_id=InputChannel.IRIS,
        enabled=True,
    )
    InputChannelApplicantType.objects.get_or_create(
        applicant_type_id=ApplicantType.COLECTIUS,
        input_channel_id=InputChannel.IRIS,
        enabled=True,
    )
