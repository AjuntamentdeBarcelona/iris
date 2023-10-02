from iris_masters.models import InputChannel


def check_input_channels(sender, **kwargs):
    input_channels = [
        {"id": InputChannel.IRIS, "description": "IRIS", "user_id": "IRIS", "order": 1, "deleted": None,
         "visible": True},
        {"id": InputChannel.ALTRES_CANALS, "description": "ALTRES CANALS", "user_id": "IRIS", "order": 100,
         "deleted": None, "visible": True},
        {"id": InputChannel.RECLAMACIO_INTERNA, "description": "RECLAMACIÓ INTERNA", "user_id": "IRIS", "order": 101,
         "deleted": None, "visible": True},
    ]

    for input_channel in input_channels:
        db_input_channel, _ = InputChannel.all_objects.get_or_create(id=input_channel["id"], defaults={
            "description": input_channel["description"], "deleted": input_channel["deleted"],
            "order": input_channel["order"], "visible": input_channel["visible"], "user_id": input_channel["user_id"]})
        if db_input_channel.deleted:
            InputChannel.all_objects.filter(pk=db_input_channel.pk).update(deleted=None)
