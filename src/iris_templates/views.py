from bs4 import BeautifulSoup
from django.db.models import Prefetch, Q
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils import translation

from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from communications.views import ANSWER_LINK_TAG
from iris_masters.models import ResponseType, ResponseChannel, Parameter
from iris_masters.serializers import ResponseTypeSerializer, DummySerializer
from iris_masters.views import BasicMasterViewSet, BasicMasterSearchMixin, BasicMasterListApiView
from iris_templates.answer import get_footer, get_header
from iris_templates.data_checks.visible_parameters import TEXT_CIM_ANSWER, TEXT_CIM
from iris_templates.models import IrisTemplate, IrisTemplateRecordTypes
from iris_templates.permissions import OWN_TEMPLATES
from iris_templates.renderer import Iris1TemplateRenderer
from iris_templates.serializers import (IrisTemplateSerializer, IrisTemplateShortSerializer, VariableSerializer,
                                        IrisRecordTextSerializer, ApplicantCommunicationTextSerializer,
                                        SaveForRecordSerializers)
from iris_templates.template_params import get_template_param
from iris_templates.templates_context.context import IrisVariableFinder, IrisApplicantCommunicationsVariableFinder
from main.api.pagination import IrisMaxPagination
from main.api.schemas import (create_swagger_auto_schema_factory, update_swagger_auto_schema_factory,
                              destroy_swagger_auto_schema_factory)
from main.utils import SPANISH, GALICIAN, ENGLISH
from profiles.permissions import IrisPermission
from record_cards.models import RecordCard


class IrisTemplateViewset(BasicMasterSearchMixin, BasicMasterViewSet):
    """
    Viewset (CRUD) to manage IRIS Templates
    The list endpoint includes a search param (?search) by description
    """
    queryset = IrisTemplate.objects.filter(group__isnull=True).select_related("response_type")
    serializer_class = IrisTemplateSerializer
    search_fields = ["#description"]
    pagination_class = IrisMaxPagination


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ResponseTypeSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ResponseTypeSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ResponseTypeSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
class ResponseTypeViewSet(BasicMasterSearchMixin, BasicMasterViewSet):
    """
    CRUD endpoints for ResponseType model, which apply the soft-delete thecnique.
    The list endpoint includes a search param (?search) by description
    """
    queryset = ResponseType.objects.all().prefetch_related(
        Prefetch("iristemplate_set", queryset=IrisTemplate.objects.all()))
    serializer_class = ResponseTypeSerializer
    search_fields = ["#description"]


class RecordTypeTemplatesListView(BasicMasterSearchMixin, BasicMasterListApiView):
    """
    Giving a recordType, it returns a list with all the available templates
    """
    serializer_class = IrisTemplateShortSerializer
    search_fields = ["#description"]

    def get_queryset(self):
        iris_templates_pks = IrisTemplateRecordTypes.objects.filter(
            record_type_id=self.kwargs["id"], enabled=True, iris_template__deleted__isnull=True
        ).select_related("iris_template").values_list("iris_template_id")
        return IrisTemplate.objects.filter(pk__in=iris_templates_pks).select_related("response_type")


class RecordCardTemplateMixin:
    """
    :todo: adapt to any language
    """
    template_renderer_class = None

    @cached_property
    def record_card(self):
        if "record_id" not in self.kwargs:
            return RecordCard.objects.select_related(
                "recordcardresponse", "request__applicant", "element_detail").first()

        return RecordCard.objects.select_related(
            "recordcardresponse", "request__applicant", "element_detail",
        ).get(pk=self.kwargs.get("record_id"))

    @cached_property
    def response_channel(self):
        if hasattr(self.record_card, "recordcardresponse"):
            return self.record_card.recordcardresponse.get_response_channel()
        return ResponseChannel.NONE

    @cached_property
    def answer_medium(self):
        if self.response_channel == ResponseChannel.SMS:
            return "sms"
        if self.response_channel in [ResponseChannel.EMAIL, ResponseChannel.LETTER]:
            return "write"
        return None

    @cached_property
    def language_code(self):
        resp = getattr(self.record_card, 'recordcardresponse', None)
        if not resp:
            return GALICIAN
        return getattr(resp, 'language', GALICIAN)

    @cached_property
    def language(self):
        if self.language_code == SPANISH:
            return "spanish"
        elif self.language_code == ENGLISH:
            return 'english'
        return "catalan"

    def get_renderer(self):
        return self.template_renderer_class(record_card=self.record_card)

    @cached_property
    def text_attribute(self):
        """
        :return: Source template attribute for rendering the answer.
        :rtype: str
        """
        if not self.answer_medium:
            return None
        return "{}_medium_{}".format(self.answer_medium, self.language)

    @cached_property
    def theme_answer_attribute(self):
        """
        :return: Source template attribute for rendering the answer.
        :rtype: str
        """
        if not self.answer_medium:
            return None
        answer_medium = self.answer_medium if self.answer_medium == "sms" else "email"
        return "{}_template_{}".format(answer_medium, self.language_code)

    def is_template_record_card(self):
        return not self.answer_medium


class RecordCardTemplatesListView(RecordCardTemplateMixin, BasicMasterSearchMixin, BasicMasterListApiView):
    """
    Giving a recordType, it returns a list with all the available templates
    """
    serializer_class = IrisRecordTextSerializer
    search_fields = ["#description"]
    permission_classes = []
    template_renderer_class = Iris1TemplateRenderer
    excluded_channels = [ResponseChannel.NONE, ResponseChannel.TELEPHONE]

    def dispatch(self, request, *args, **kwargs):
        current = translation.get_language()
        translation.activate(self.language_code)
        resp = super().dispatch(request, *args, **kwargs)
        translation.activate(current)
        return resp

    def paginate_queryset(self, queryset):
        qs = super().paginate_queryset(queryset)
        own_answer = self.get_theme_answer(self.record_card)
        if own_answer:
            return list(qs) + [own_answer]
        return self.set_default(list(qs))

    @cached_property
    def default_answer_type(self):
        try:
            return ResponseType.objects.get(pk=Parameter.get_parameter_by_key("TIPUS_RESPOSTA_DEFECTE", 1))
        except ResponseType.DoesNotExist:
            return None

    def set_default(self, templates):
        if self.default_answer_type:
            for template in templates:
                if template.response_type_id == self.default_answer_type.id:
                    setattr(template, "is_default", True)
        return templates

    def get_queryset(self):
        if not self.has_templates:
            return IrisTemplate.objects.none()
        return IrisTemplate.objects.filter(
            Q(iristemplaterecordtypes__record_type_id=self.record_card.record_type_id, group__isnull=True)
            | Q(group=self.request.user.usergroup.group)
        ).exclude(**{self.text_attribute: ""}).select_related("response_type").distinct()

    @property
    def has_templates(self):
        return hasattr(self.record_card, "recordcardresponse") \
               and self.record_card.recordcardresponse.get_response_channel() not in self.excluded_channels

    @cached_property
    def is_sms(self):
        return self.response_channel == ResponseChannel.SMS

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["rendered_template_attribute"] = self.text_attribute
        ctx["template_renderer"] = self.get_renderer()
        ctx["language"] = self.language_code
        ctx["record_card"] = self.record_card
        ctx["is_sms"] = self.is_sms
        return ctx

    def get_theme_answer(self, record):
        """
        Each theme defines its own answer text that can be selected within the manage answer templates.
        :param record:
        :return: Theme own answer text
        """
        if not self.has_templates:
            return None

        if record.element_detail.custom_answer:
            return None

        text = getattr(record.element_detail, self.theme_answer_attribute, None)
        if not text:
            return None

        if self.is_sms:
            text = BeautifulSoup(text, "html.parser").get_text()

        answer = IrisTemplate(**{self.text_attribute: text})
        setattr(answer, "is_own", True)
        setattr(answer, "is_default", True)
        return answer


@method_decorator(name="get", decorator=swagger_auto_schema(
    operation_id="Templates Variables list",
    responses={
        HTTP_200_OK: VariableSerializer(many=True),
    }
))
class VariablesListView(APIView):
    """
    Retrieve the list of variables that can be used on an iris template
    """
    serializer_class = VariableSerializer
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(self.serializer_class(instance=self.get_templates_variables(), many=True).data,
                        status=HTTP_200_OK)

    @staticmethod
    def get_templates_variables():
        """
        Gets the list of variables that can be used on iris template from the Config Finder and Record Finder

        :return: A list of variables ready to be serialized
        """
        return [{"name": value} for value in IrisVariableFinder().get_vars_for_templates()]


class RecordVariableView(RetrieveAPIView):
    """
    View to retrieve the variables for a template of a given RecordCard.
    The fields returned will depend on the record_card.
    """
    queryset = RecordCard.objects.all()
    lookup_url_kwarg = 'record_id'
    lookup_field = 'normalized_record_id'
    serializer_class = DummySerializer

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.get_templates_variables(instance), status=HTTP_200_OK)

    @staticmethod
    def get_templates_variables(record_card):
        """
        Gets the list of variables for a Record

        :return: An object of variables ready to be serialized
        """
        finder = IrisVariableFinder(record_card)
        return finder.get_values({}, finder.get_vars_for_templates())


class ApplicantCommunicationTemplate(RecordCardTemplateMixin, RetrieveAPIView):
    """
    Retrieve the template for an applicant communication
    """
    model = RecordCard
    serializer_class = ApplicantCommunicationTextSerializer
    template_renderer_class = Iris1TemplateRenderer
    LANGS = {
        'ca': 'CAT',
        'es': 'CAST',
        'en': 'ANG',
    }

    def get_object(self):
        answer = {
            "header": self.get_header(),
            "footer": self.get_footer(),
            "simple_body": self.get_simple_body(),
            "answer_body": self.get_answer_body(),
            "answer_tag": ANSWER_LINK_TAG,
        }
        renderer = self.get_renderer()
        for key in answer:
            answer[key] = renderer.render(answer[key])
        return answer

    def get_parameter(self, param):
        return get_template_param(self.language_code, param)

    def get_simple_body(self):
        return self.get_parameter(TEXT_CIM)

    def get_answer_body(self):
        return self.get_parameter(TEXT_CIM_ANSWER)

    def get_renderer(self):
        return self.template_renderer_class(record_card=self.record_card,
                                            var_finder_cls=IrisApplicantCommunicationsVariableFinder)

    def get_header(self):
        return get_header(self.request.user.usergroup.group, self.language_code)

    def get_footer(self):
        return get_footer(self.request.user.usergroup.group, self.language_code)


class SaveForRecordView(RecordCardTemplateMixin, UpdateAPIView):
    """
    View to update the templates of IRIS2.
    OWN_TEMPLATES permission is needed to do the action.
    There's a maximum number of templates that a group can have given by the Parameter TEMP_MAX_GROUP.
    """
    queryset = IrisTemplate.objects.all()
    serializer_class = SaveForRecordSerializers

    def get_object(self):
        try:
            return super().get_object()
        except (AssertionError, IrisTemplate.DoesNotExist):
            self.check_template_limit()
            return self.create_template()

    def get_permissions(self):
        return [IrisPermission(OWN_TEMPLATES)]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return super().get_queryset()

        return super().get_queryset().filter(group=self.request.user.usergroup.group)

    def check_template_limit(self):
        template_count = self.get_queryset().count()
        if Parameter.get_parameter_by_key("TEMP_MAX_GROUP", 10) == template_count:
            raise ValidationError(_("You have exceeded the number of templates for this group."))

    def create_template(self):
        return IrisTemplate(
            group=self.request.user.usergroup.group
        )

    def get_serializer(self, *args, **kwargs):
        data = kwargs.get("data", {})
        kwargs["data"] = {
            self.text_attribute: data.get("text"),
            "description": data.get("description"),
        }
        return super().get_serializer(*args, **kwargs)
