from features.models import Feature
from iris_masters.data_checks.parameters import create_parameter_list
from iris_masters.models import Parameter, Process, InputChannel, Support, InputChannelSupport
from themes.models import ElementDetail, ElementDetailFeature, Element, Area

MIB_ORIGIN = "MIB_ORIGIN"
MIB_ENABLED = "MIB_ENABLED"


def check_integrations_parameters(sender, **kwargs):
    parameters = [
        {"user_id": "IRIS2", "parameter": "TWITTER_THEME_APPLICATION", "valor": "100",
         "description": "Aplicación para filtrar las temáticas seleccionables a flujo de Twitter. El valor debe"
                        "ser un entero",
         "name": "Twitter - Aplicación para filtrar temáticas",
         "original_description": "Aplicación para filtrar las temáticas seleccionables a flujo de Twitter. "
                                 "El valor debe ser un entero", "show": True,
         "data_type": False, "visible": True, "category": Parameter.INTEGRATIONS},
        {"user_id": "IRIS2", "parameter": "TWITTER_RESPONSE_TEXT",
         "valor": "Para gestionar la petición necesitamos información adicional. "
                  "Hazla llegar al Ayuntamiento ¡Gracias por tu colaboración!",
         "description": "Texto de respuesta al ciudadano para obtener más información vía twitter",
         "name": "Comunicaciones - Twitter - Texto de respuesta Twitter",
         "original_description": "Texto de respuesta al ciudadano para obtener más información vía twitter",
         "show": True, "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS},
        {"user_id": "IRIS2", "parameter": "EMAILS_ERROR_XALOC", "valor": "",
         "description": "Listado de emails a los que avisar si falla la integración con Xaloc. "
                        "Los valores deben ir separados por comas",
         "name": "Xaloc - Listado de emails error Xaloc",
         "original_description": "Listado de emails a los que avisar si falla la integración con Xaloc. "
                        "Los valores deben ir separados por comas",
         "show": True, "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS}
    ]
    create_parameter_list(parameters)
    create_twitter_theme()
    create_twitter_input()


def create_twitter_theme():
    try:
        Parameter.objects.get(parameter="TWITTER_ELEMENT_DETAIL")
    except Parameter.DoesNotExist:
        Process.objects.get_or_create(id=Process.CLOSED_DIRECTLY)
        element_detail = ElementDetail.objects.create(
            element=Element.objects.create(
                description="Twitter",
                area=Area.objects.create(description="Twitter"),
            ),
            description="Twitter",
            process_id=Process.CLOSED_DIRECTLY,
        )
        feature = Feature.objects.create(
            description="ID Twitter (@id)",
            is_special=False,
            explanatory_text="",
            visible_for_citizen=False,
            editable_for_citizen=False,
        )
        ElementDetailFeature.objects.create(
            element_detail=element_detail,
            feature=feature,
            is_mandatory=True,
            order=0,
            enabled=True,
        )
        Parameter.objects.create(**{
            "user_id": "IRIS2", "parameter": "TWITTER_ELEMENT_DETAIL", "valor": element_detail.pk,
            "description": "Twitter - id de detalle. El valor debe ser un entero que haga referencia al detalle del "
                           "elemento correspondiente",
            "name": "Twitter - id de detall",
            "original_description": "Twitter - id de detalle. El valor debe ser un entero que "
                                    "haga referencia al detalle de elemento correspondiente", "show": True,
            "data_type": False, "visible": True, "category": Parameter.INTEGRATIONS
        })
        Parameter.objects.create(**{
            "user_id": "IRIS2", "parameter": "TWITTER_ATTRIBUTE", "valor": feature.pk,
            "description": "Twitter - id del atributo con el usuario. El valor debe ser un entero que haga "
                           "referencia al atributo correspondiente",
            "name": "Twitter - id del atributo con el usuario",
            "original_description": "Twitter - id del atributo con el usuario. El valor debe ser un entero que haga "
                           "referencia al atributo correspondiente", "show": True,
            "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS
        })


def create_twitter_input():
    try:
        Parameter.objects.get(parameter="TWITTER_INPUT_CHANNEL")
    except Parameter.DoesNotExist:
        input_channel = InputChannel.objects.create(description="Twitter")
        Parameter.objects.create(**{
            "user_id": "IRIS2", "parameter": "TWITTER_INPUT_CHANNEL",
            "valor": input_channel.pk,
            "description": "Twitter - Id Canal de Entrada. El valor debe ser un entero que haga "
                           "referencia al Canal de Entrada correspondiente",
            "name": "Twitter - Id Canal de Entrada",
            "original_description": "Twitter - Id Canal de Entrada. El valor debe ser un entero que haga "
                           "referencia al Canal de Entrada correspondiente", "show": True,
            "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS
        })

        try:
            Parameter.objects.get(parameter="TWITTER_SUPPORT")
        except Parameter.DoesNotExist:
            support = Support.objects.create(description="Twitter")
            InputChannelSupport.objects.create(
                input_channel=input_channel,
                support=support,
                enabled=True,
            )
            Parameter.objects.create(**{
                "user_id": "IRIS2", "parameter": "TWITTER_SUPPORT", "valor": support.id,
                "description": "Twitter - Id de soporte. El valor debe ser un entero que haga "
                           "referencia al Soporte correspondiente",
                "name": "Twitter - Id de soporte",
                "original_description": "Twitter - Id de soporte. El valor debe ser un entero que haga "
                           "referencia al Soporte correspondiente", "show": True,
                "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS
            },)
