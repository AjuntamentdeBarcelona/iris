from iris_masters.models import Parameter, Process, ResponseChannel, Application, RecordType
from themes.models import Area, ElementDetail, Element, ElementDetailResponseChannel


def check_survey(sender, **kwargs):
    ed_id = Parameter.get_parameter_by_key("IRIS_ENQUESTA", None)
    try:
        ed = ElementDetail.objects.get(pk=ed_id)
    except ElementDetail.DoesNotExist:
        area, _ = Area.objects.get_or_create(description='Encuesta')
        element, _ = Element.objects.get_or_create(description='Encuesta interna', area=area)
        ed = ElementDetail.objects.create(
            pk=ed_id,
            description='Encuesta',
            element=element,
            process_id=Process.RESPONSE,
            active=True,
            visible=True,
            record_type_id=RecordType.SUGGESTION,
        )
    ElementDetailResponseChannel.objects.get_or_create(
        elementdetail=ed,
        responsechannel_id=ResponseChannel.NONE,
        application_id=Application.IRIS_PK,
        enabled=True,
    )

