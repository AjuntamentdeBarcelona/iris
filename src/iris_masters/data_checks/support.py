
from iris_masters.models import Support, InputChannel, InputChannelSupport


def check_required_support(sender, **kwargs):

    required_supports = {
        Support.IRIS: {"user_id": "IMI", "description": "IRIS", "order": 18, "communication_media_required": False},
        Support.EMAIL: {"user_id": "IMI", "description": "EMAIL", "order": 18, "communication_media_required": False},
        Support.PHONE: {
            "user_id": "IMI", "description": "TELÉFONO", "order": 18, "communication_media_required": False
        },
        Support.LETTER: {"user_id": "IMI", "description": "CARTA", "order": 18, "communication_media_required": False},
        Support.WEB: {"user_id": "IMI", "description": "WEB", "order": 18, "communication_media_required": False},
        Support.RECLAMACIO_INTERNA: {"user_id": "IRIS", "description": "RECLAMACIÓN INTERNA",
                                     "order": 20, "communication_media_required": False},
        Support.COMMUNICATION_MEDIA: {"user_id": "IMI", "description": "MEDIOS DE COMUNICACIÓN",
                                      "order": 13, "communication_media_required": True},
        Support.ALTRES_MITJANS: {"user_id": "IMI", "description": "OTROS MEDIOS",
                                 "order": 19, "communication_media_required": False}
    }

    for (support_id, support_data) in required_supports.items():
        support, _ = Support.objects.get_or_create(
            id=support_id,
            defaults={"user_id": support_data["user_id"],
                      "description": support_data["description"],
                      "order": support_data["order"],
                      "communication_media_required": support_data["communication_media_required"]
                      })
        if support.communication_media_required != support_data.get("communication_media_required", False):
            support.communication_media_required = support_data.get("communication_media_required", False)
            support.save()

    InputChannelSupport.objects.get_or_create(
        support_id=Support.RECLAMACIO_INTERNA,
        input_channel_id=InputChannel.RECLAMACIO_INTERNA,
        enabled=True,
    )
    required_supports.pop(Support.RECLAMACIO_INTERNA)
    for sup_id in required_supports.keys():
        InputChannelSupport.objects.get_or_create(
            support_id=sup_id,
            input_channel_id=InputChannel.IRIS,
            enabled=True,
        )
