import base64
import json
import logging
import re

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404
from django.utils import timezone, translation
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from django.conf import settings

from rest_framework import filters
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404, CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_201_CREATED, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST, HTTP_200_OK,
                                   HTTP_404_NOT_FOUND)
from rest_framework.views import APIView

from communications.models import Message, Conversation
from integrations.services.mario.services import MarioService
from iris_masters.models import (RecordState, ApplicantType, InputChannel, District, Support, RecordType,
                                 ResponseChannel, Reason, FurniturePickUp, Parameter, Application)
from iris_masters.serializers import FurniturePickUpSerializer
from main.api.pagination import IrisPagination
from main.api.schemas import create_swagger_auto_schema_factory
from main.iris_roles import public_iris_roles
from main.utils import SPANISH, get_user_traceability_id
from profiles.models import Group
from profiles.tasks import send_allocated_notification
from public_api.constants import TRANSACTION_URGENT
from public_api.filters import ElementDetailPublicFilter, RecordCardPublicFilter, MarioPublicFilter
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.models import (RecordCard, Request, RecordCardFeatures, Ubication, RecordCardSpecialFeatures,
                                 Applicant, Citizen, SocialEntity, RecordCardResponse, Comment, RecordFile,
                                 InternalOperator)
from record_cards.record_actions.claim_validate import ClaimValidation
from record_cards.record_actions.normalized_reference import set_reference
from record_cards.serializers import ClaimDescriptionSerializer
from record_cards.tasks import save_last_applicant_response, geocode_ubication
from record_cards.record_actions.geocode import get_geocoder_services_class

from themes.actions.theme_keywords_search import KeywordSearch

from themes.models import Area, ElementDetail, Element, ApplicationElementDetail, ElementDetailFeature
from .caches import ElementDetailListCache
from .pagination import ElementFavouritePagination
from .serializers import (AreaPublicSerializer, ElementDetailRetrievePublicSerializer,
                          ElementPublicSerializer, RecordCardRetrievePublicSerializer, RecordCardCreatePublicSerializer,
                          RecordCardCreatedPublicSerializer, DistrictPublicSerializer,
                          RecordCardRetrieveStatePublicSerializer, RecordCardSSIPublicSerializer,
                          RecordTypePublicSerializer, ClaimResponseSerializer, ElementDetailLastUpdateSerializer,
                          InputChannelPublicSerializer, ApplicantTypePublicSerializer,
                          RecordCardMobileCreatePublicSerializer, RecordCardResponsePublicSerializer,
                          RecordCardMobileCreatedPublicSerializer, MessageShortHashSerializer,
                          MessageHashCreateSerializer, ParameterPublicSerializer, ElementDetailRegularPublicSerializer,
                          RecordCardMinimalPublicSerializer)


logger = logging.getLogger(__name__)


class PublicApiListAPIView(ListAPIView):
    permission_classes = (AllowAny,)


@method_decorator(name="get", decorator=public_iris_roles)
class AreaList(PublicApiListAPIView):
    """
    List of Areas for ATE application
    """
    serializer_class = AreaPublicSerializer

    def get_queryset(self):
        area_pks = ApplicationElementDetail.objects.get_areapks_byapp(self.request.application)
        return Area.objects.filter(pk__in=area_pks).order_by("description")


@method_decorator(name="get", decorator=public_iris_roles)
class ElementFavouriteList(PublicApiListAPIView):
    """
    List of favorited Elements for ATE application
    """

    serializer_class = ElementPublicSerializer
    pagination_class = ElementFavouritePagination

    def get_queryset(self):
        elements_pk = ApplicationElementDetail.objects.get_elementpks_byapp(self.request.application)
        return Element.objects.filter(
            pk__in=elements_pk, is_favorite=True).select_related("area").order_by("description")


@method_decorator(name="get", decorator=public_iris_roles)
class ElementList(PublicApiListAPIView):
    """
    List of Element for ATE application. If area_id is in query params, it only returns the element of this area.
    """

    serializer_class = ElementPublicSerializer

    def get_queryset(self):
        area_id = self.request.query_params.get("area_id")
        if area_id:
            elements_pk = ApplicationElementDetail.objects.get_elementpks_byapp(self.request.application)
            return Element.objects.filter(
                pk__in=elements_pk, area_id=area_id).select_related("area").order_by("description")
        else:
            elements_pk = ApplicationElementDetail.objects.get_elementpks_byapp(self.request.application)
            return Element.objects.filter(
                pk__in=elements_pk).select_related("area").order_by("description")


@method_decorator(name="get", decorator=public_iris_roles)
class ElementDetailSearchView(PublicApiListAPIView):
    """
    Paginated list of ElementDetails that can be displayed on the ATE.
    The list can be filtered by area_id and element_id and searched by description.
    When the list is filtered by area_id, the pagination is omited.
    """
    filter_backends = (filters.SearchFilter, DjangoFilterBackend)
    serializer_class = ElementDetailRegularPublicSerializer
    filterset_class = ElementDetailPublicFilter

    @property
    def search_fields(self):
        return [f'description_{lang}' for lang, _ in settings.LANGUAGES]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        area_filter = request.GET.get("area_id")

        cache = ElementDetailListCache()
        application = self.request.application
        if not area_filter:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, cache=cache, application=application)
                return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, cache=cache, application=application)
        return Response(serializer.data)

    def get_queryset(self):
        element_details_pks = ApplicationElementDetail.objects.get_elementdetailpks_byapp(self.request.application)
        return ElementDetail.objects.filter(pk__in=element_details_pks, visible=True, active=True).order_by(
            "element__description", "element_id", "description").select_related("element").prefetch_related(
            Prefetch("feature_configs",
                     ElementDetailFeature.objects.filter(enabled=True, feature__deleted__isnull=True,
                                                         feature__visible_for_citizen=True
                                                         ).select_related(
                         "feature", "feature__mask", "feature__values_type").order_by("-is_mandatory")))


@method_decorator(name="get", decorator=public_iris_roles)
class ElementDetailRetrieveView(RetrieveAPIView):
    """
    Retrieve the detail of an ElementDetail. The ElementDetail must be on ATE, WEB_DIRECT or CONSULTES_DIRECTO
    application.
    """
    serializer_class = ElementDetailRetrievePublicSerializer
    permission_classes = (AllowAny,)
    queryset = ElementDetail.objects.filter(visible=True).select_related("element", "element__area", "record_type")


@method_decorator(name="get", decorator=public_iris_roles)
class ElementDetailLastUpdated(APIView):
    """
    Endpoint to retrieve the last time that an ElementDetail of ATE application has been updated.
    """

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        element_details_pks = ApplicationElementDetail.objects.get_elementdetailpks_byapp(self.request.application)
        element_detail = ElementDetail.objects.filter(pk__in=element_details_pks).order_by("-updated_at").first()
        return Response(ElementDetailLastUpdateSerializer(element_detail).data, status=HTTP_200_OK)


@method_decorator(name="get", decorator=public_iris_roles)
class RecordCardRetrieveView(RetrieveAPIView):
    """
    Endpoint to retrieve a RecordCard by ID
    """
    serializer_class = RecordCardRetrievePublicSerializer
    queryset = RecordCard.objects.filter(enabled=True).select_related(
        "record_state", "ubication", "recordcardresponse"
    ).prefetch_related(
        Prefetch("recordcardfeatures_set",
                 RecordCardFeatures.objects.filter(enabled=True, feature__deleted__isnull=True).select_related(
                     "feature", "feature__mask", "feature__values_type")),
        Prefetch("recordcardspecialfeatures_set",
                 RecordCardSpecialFeatures.objects.filter(enabled=True, feature__deleted__isnull=True).select_related(
                     "feature", "feature__mask", "feature__values_type")))
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> RecordCard:
        reference = self.kwargs.get("reference", None)
        if reference:
            rc = get_object_or_404(self.queryset, normalized_record_id=reference)
            self.check_object_permissions(self.request, rc)
            return rc
        return super().get_object()


@method_decorator(name="get", decorator=public_iris_roles)
class RecordCardRetrieveStateView(RetrieveAPIView):
    """
    Endpoint to retrieve the state of a RecordCard.
    """
    serializer_class = RecordCardRetrieveStatePublicSerializer
    queryset = RecordCard.objects.filter(enabled=True).select_related("record_state")
    permission_classes = (AllowAny,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        message_hash = self.request.GET.get("hash")
        if message_hash:
            try:
                context["message"] = Message.objects.get(hash=message_hash,
                                                         conversation__type__in=Conversation.HASH_TYPES)
            except Message.DoesNotExist:
                pass
        return context


class SetFeaturesMixin:

    @staticmethod
    def set_features(record_card, features):
        for feature_data in features:
            feature = feature_data["id"]
            if feature.is_special:
                RecordCardSpecialFeatures.objects.create(feature=feature, record_card=record_card,
                                                         value=feature_data["value"])
            else:
                RecordCardFeatures.objects.create(feature=feature, record_card=record_card,
                                                  value=feature_data["value"])


class CheckFileSizeMixin:

    @staticmethod
    def get_file_max_size() -> int:
        """

        :return: File max size in KB
        """
        return int(Parameter.get_parameter_by_key("FITXERS_MIDA_MAXIMA_IMG", 6145))

    @staticmethod
    def check_file_size(content_file, file_max_size_kb) -> bool:
        """

        :param content_file:
        :param file_max_size_kb:
        :return: True if file size is smaller or equal than max allowed size
        """
        return content_file.size <= file_max_size_kb * 1024


class SetBase64AttachmentsMixin(CheckFileSizeMixin):

    def set_attachments(self, attachments, record_card):
        file_max_size_kb = self.get_file_max_size()
        for file in attachments:
            content_file = ContentFile(base64.b64decode(file["data"]), name=file["filename"])
            if not self.check_file_size(content_file, file_max_size_kb):
                raise ValidationError(_("Files can not be greather than {} KB").format(file_max_size_kb))
            RecordFile.objects.create(file=content_file, record_card_id=record_card.id,
                                      filename=file["filename"], user_id=get_user_traceability_id(self.request.user),
                                      file_type=RecordFile.WEB)


class SetFilesMixin(CheckFileSizeMixin):
    def set_files(self, files, record_card):
        file_max_size_kb = self.get_file_max_size()
        for file in files:
            content_file = file["file"]
            if not self.check_file_size(content_file, file_max_size_kb):
                raise ValidationError(_("Files can not be greather than {} KB").format(file_max_size_kb))
            RecordFile.objects.create(file=content_file, record_card_id=record_card.id,
                                      filename=file["filename"], user_id=get_user_traceability_id(self.request.user),
                                      file_type=RecordFile.WEB)


class ApplicantBlockedMixin:
    @staticmethod
    def check_applicant_blocked(applicant, element_detail):
        no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
        if applicant.blocked and no_block_theme_pk != element_detail.pk:
            return Response({"non_field_errors": _("Applicant can not be used to create a record because "
                                                   "it's blocked")}, status=HTTP_400_BAD_REQUEST)


class InternalOperatorMixin:

    def is_internal_operator(self, applicant, applicant_type_id, input_channel_id):
        return InternalOperator.objects.filter(
            document=applicant.document, applicant_type_id=applicant_type_id, input_channel_id=input_channel_id
        ).exists()

    @cached_property
    def default_applicant(self):
        default_dni = Parameter.get_parameter_by_key("AGRUPACIO_PER_DEFECTE", "GUB")
        try:
            return Applicant.objects.get(citizen__dni=default_dni)
        except Applicant.DoesNotExist:
            return None


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(
    request_body_serializer=RecordCardCreatePublicSerializer, add_forbidden=False))
@method_decorator(name="post", decorator=public_iris_roles)
class RecordCardCreateView(InternalOperatorMixin, ApplicantBlockedMixin, SetFeaturesMixin, SetFilesMixin, APIView):
    """
    Endpoint to create a RecordCard by the ATE
    """

    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):  # noqa

        with transaction.atomic():
            data, files = self.get_request_data(request)

            record_card_create_serializer = RecordCardCreatePublicSerializer(
                data=data, context=self.set_element_detail_context(data))

            if record_card_create_serializer.is_valid(raise_exception=True):
                record_data = record_card_create_serializer.validated_data
                ubication = self.set_ubication(record_data["location"]) if record_data.get("location") else None
                GcodServices = get_geocoder_services_class()
                if ubication and GcodServices:
                    result = GcodServices().adress_validation_variable(ubication.street,
                                                                       numIni=ubication.street2,
                                                                       lletraIni=ubication.letter)

                    if result['ReturnCode'] != 1:
                        return Response({"location": _("The introduced location is wrong")},
                                        status=HTTP_400_BAD_REQUEST)
                applicant, applicant_type_id, is_internal_operator = self.get_applicant(record_data)

                applicant_blocked_response = self.check_applicant_blocked(applicant, record_data["detailId"])
                if applicant_blocked_response:
                    return applicant_blocked_response

                request = Request.objects.create(user_id=get_user_traceability_id(self.request.user),
                                                 applicant=applicant, applicant_type_id=applicant_type_id,
                                                 input_channel=self.ate_input_channel,
                                                 application=self.request.application,
                                                 normalized_id=set_reference(Request, "normalized_id"))
                logger.info(record_data.get("location", {}))
                support_id = record_data.get("device").pk if record_data.get("device") else Support.WEB

                # If Dair Group is set, the web created RecordCard will be assigned to it
                record_card = RecordCard.objects.create(
                    user_id="WEB", element_detail=record_data["detailId"], support_id=support_id,
                    description=record_data["comments"], urgent=self.set_urgency(record_data.get("transaction")),
                    applicant_type_id=applicant_type_id, request=request, record_state_id=RecordState.PENDING_VALIDATE,
                    ubication=ubication, record_type=record_data["detailId"].record_type, organization="WEB",
                    input_channel=self.ate_input_channel, page_origin=record_data["origin"],
                    responsible_profile=Group.get_initial_group_for_record()
                )
                if not ubication:
                    record_card.derivate(user_id="WEB", reason=Reason.INITIAL_ASSIGNATION)
                self.set_features(record_card, record_data.get("characteristics", []))
                record_card_response = self.set_record_card_response(record_data, record_card, is_internal_operator,
                                                                     record_data["detailId"].immediate_response)
                self.set_files(files, record_card)
                if record_card.record_can_be_autovalidated():
                    record_card.autovalidate_record('', self.request.user)

        record_card.send_record_card_created()

        if ubication:
            geocode_ubication.delay(
                ubication.pk,
                derivate_id=record_card.id,
                user_id="WEB",
                reason=Reason.INITIAL_ASSIGNATION,
            )
        save_last_applicant_response.delay(applicant.pk, record_card_response.pk,
                                           record_data.get("authorization", False))
        return Response(RecordCardCreatedPublicSerializer(record_card).data, status=HTTP_201_CREATED)

    def get_request_data(self, request):
        data = {}
        if "body" in request.data:
            data.update(json.loads(request.data.get("body")))
        else:
            data.update(request.data)
        files = [{"filename": file.name, "file": file} for _, file in request.FILES.items()]
        data.update({"pictures": files})
        return data, files

    @cached_property
    def ate_input_channel(self):
        input_channel_id = int(Parameter.get_parameter_by_key("CANAL_ENTRADA_ATE", 7))
        try:
            return InputChannel.objects.get(pk=input_channel_id)
        except InputChannel.DoesNotExist:
            return InputChannel.objects.create(pk=input_channel_id, description="INTERNET. BÚSTIA CIUTADANA", order=55,
                                               visible=False, can_be_mayorship=False)

    def set_element_detail_context(self, data):
        try:
            kwargs = ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy()
            kwargs["pk"] = data.get("detailId")
            return {"element_detail": ElementDetail.objects.get(**kwargs)}
        except ElementDetail.DoesNotExist:
            return {}

    @staticmethod
    def set_ubication(location_data):
        try:
            ubication = Ubication.objects.get(pk=location_data["id"], enabled=True)
        except (Ubication.DoesNotExist, KeyError):
            ubication = Ubication()

        ubication.latitude = location_data.get("latitude", "")
        ubication.longitude = location_data.get("longitude", "")
        ubication.geocode_district_id = location_data.get("geocode", "")
        ubication.via_type = location_data.get("via_type", "")
        ubication.street = location_data.get("address", "")
        number = location_data.get("number", "")
        letter = ''
        if number:
            if re.split('(\d+)', number.strip())[2] == '-':  # noqa
                number = re.split('(\d+)', number.strip())[1]  # noqa
                letter = ''
            elif re.split('(\d+)', number.strip())[2] not in ('-', ''):  # noqa
                letter = re.split('(\d+)', number.strip())[2].strip('-')  # noqa
                number = re.split('(\d+)', number.strip())[1]  # noqa
        ubication.street2 = number
        ubication.letter = letter
        ubication.floor = location_data.get("floor", "")
        ubication.door = location_data.get("door", "")
        ubication.stair = location_data.get("stair", "")
        ubication.district = location_data.get("district")
        ubication.save()
        logging.info(f'UBICATION WITH ADDRESS {ubication.street} FROM  {location_data.get("street", "")}')
        return ubication

    def get_applicant(self, record_data):
        if record_data.get("applicant"):
            applicant = record_data["applicant"]
        elif record_data.get("nameCitizen"):
            applicant = self.set_citizen_applicant(record_data)
        else:
            # the last case social entity applicant
            applicant = self.set_socialentity_applicant(record_data)

        applicant_type_id = self.get_applicant_type(applicant)
        is_internal_operator = self.is_internal_operator(applicant, applicant_type_id, self.ate_input_channel.pk)
        if is_internal_operator and self.default_applicant:
            applicant = self.default_applicant
        return applicant, applicant_type_id, is_internal_operator

    @staticmethod
    def get_applicant_type(applicant):
        return ApplicantType.CIUTADA if applicant.citizen else ApplicantType.COLECTIUS

    @staticmethod
    def set_citizen_applicant(record_data):
        try:
            citizen = Citizen.objects.get(dni=record_data.get("numberDocument").upper())
        except Citizen.DoesNotExist:
            citizen = Citizen.objects.create(name=record_data.get("nameCitizen"),
                                             first_surname=record_data.get("firstSurname"),
                                             second_surname=record_data.get("secondSurname"),
                                             doc_type=record_data.get("typeDocument"),
                                             dni=record_data.get("numberDocument"),
                                             birth_year=record_data.get("birth_year"),
                                             sex=record_data.get("sex", Citizen.UNKNOWN),
                                             district_id=record_data.get("district"),
                                             language=record_data.get("language", SPANISH))
        except Citizen.MultipleObjectsReturned:
            citizen = Citizen.objects.filter(dni=record_data.get("numberDocument").upper()).first()
        if citizen:
            existent = Applicant.objects.filter(citizen=citizen).first()
            if existent:
                return existent
            return Applicant.objects.create(citizen=citizen)
        raise ValidationError('Citizen is mandatory')

    @staticmethod
    def set_socialentity_applicant(record_data):
        try:
            social_entity = SocialEntity.objects.get(cif=record_data.get("cif").upper())
        except SocialEntity.DoesNotExist:
            social_entity = SocialEntity.objects.create(social_reason=record_data.get("socialReason"),
                                                        contact=record_data.get("contactPerson"),
                                                        cif=record_data.get("cif"),
                                                        district_id=record_data.get("district"),
                                                        language=record_data.get("language", SPANISH))
        except SocialEntity.MultipleObjectsReturned:
            social_entity = SocialEntity.objects.filter(cif=record_data.get("cif").upper()).first()
        if social_entity:
            existent = Applicant.objects.filter(social_entity=social_entity).first()
            if existent:
                return existent
            return Applicant.objects.create(social_entity=social_entity)
        raise ValidationError('Social entity is mandatory')

    @staticmethod
    def set_urgency(transaction_value):
        return True if transaction_value and transaction_value.upper() == TRANSACTION_URGENT else False

    @staticmethod
    def set_record_card_response(record_data, record_card, is_internal_operator, theme_immediate_response):
        if record_data.get("email"):
            email = record_data.get("email")
            telephone = None
        elif record_data.get("telephone"):
            telephone = record_data.get("telephone")
            email = None
        else:
            email = None
            telephone = None
        if email:
            response_channel_id = ResponseChannel.EMAIL
            address_mobile_email = email
        elif telephone:
            response_channel_id = ResponseChannel.SMS
            address_mobile_email = telephone
        else:
            response_channel_id = ResponseChannel.NONE
            address_mobile_email = ""

        if is_internal_operator:
            response_channel_id = ResponseChannel.NONE

        if theme_immediate_response:
            response_channel_id = ResponseChannel.IMMEDIATE

        return RecordCardResponse.objects.create(response_channel_id=response_channel_id,
                                                 record_card_id=record_card.pk,
                                                 address_mobile_email=address_mobile_email,
                                                 language=record_data.get("language", SPANISH))


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(
    request_body_serializer=ClaimDescriptionSerializer,
    responses={
        HTTP_201_CREATED: ClaimResponseSerializer,
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_409_CONFLICT: "Claim can't be created",
    }))
@method_decorator(name="post", decorator=public_iris_roles)
class RecordCardClaimCreateView(APIView):
    """
    Public endpoint ot create a claim on a record_card.
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):

        claim = None
        with transaction.atomic():
            record_card = get_object_or_404(RecordCard, normalized_record_id=self.kwargs["reference"],
                                            enabled=True)

            claim_serializer = ClaimDescriptionSerializer(data=self.request.data)
            if claim_serializer.is_valid(raise_exception=True):

                try:
                    claim_validation = ClaimValidation(record_card)
                    claim_validation.validate_email(self.request.data.get('email'))
                    claim_validation.validate()
                except RecordClaimException as claim_exception:
                    if claim_exception.must_be_comment:
                        return self.create_comment_claim(record_card, claim_serializer.validated_data["description"],
                                                         claim_exception.message)
                    return Response(claim_exception.message, status=HTTP_409_CONFLICT)

                claim = record_card.create_record_claim("WEB", claim_serializer.validated_data["description"],
                                                        is_web_claim=True)
                claim.update_claims_number()
                if claim.record_can_be_autovalidated():
                    claim.autovalidate_record('', self.request.user)
                record_response = RecordCardResponse.objects.filter(record_card=claim)
                if record_response and self.request.data.get('email'):
                    em = self.request.data['email']
                    RecordCardResponse.objects.filter(record_card=claim).update(address_mobile_email=em)
                elif self.request.data.get('email'):
                    RecordCardResponse.objects.create(record_card=claim,
                                                      response_channel_id=0,
                                                      address_mobile_email=self.request.data['email'])

                data_response = {
                    "reference": claim.normalized_record_id,
                    "reason": _("The claim has been created sucesfully!")
                }
        if record_card.recordfile_set.exists():
            claim.copy_files(claim.responsible_profile, record_card.pk)
        if claim:
            send_allocated_notification.delay(claim.responsible_profile_id, claim.pk)
        return Response(ClaimResponseSerializer(data_response).data, status=HTTP_201_CREATED)

    @staticmethod
    def create_comment_claim(record_card, claim_description, response_reason):
        """
        Create a comment with the claim, if data are valid and a new claim can"t be created yet
        :param record_card: Record card where to add the comment
        :param claim_description: text to insert
        :param response_reason: text for response
        :return:
        """
        Comment.objects.create(record_card=record_card, group=None, reason_id=Reason.CLAIM_CITIZEN_REQUEST,
                               comment=claim_description)
        record_card.citizen_alarm = True
        record_card.save()
        data_response = {
            "reference": record_card.normalized_record_id,
            "reason": response_reason
        }
        return Response(ClaimResponseSerializer(data_response).data, status=HTTP_201_CREATED)


@method_decorator(name="get", decorator=public_iris_roles)
class DistrictList(PublicApiListAPIView):
    """
    Endpoint to retrieve a list of districts
    """
    queryset = District.objects.all()
    serializer_class = DistrictPublicSerializer


class IrisSSIPagination(IrisPagination):
    page_size = 4_000_000_000
    max_page_size = 4_000_000_000


@method_decorator(name="get", decorator=public_iris_roles)
class RecordCardSSIListView(PublicApiListAPIView):
    """
    List of record cards that can be displayed at SSI, as element detail has allows_ssi=True
    """
    queryset = RecordCard.objects.filter(enabled=True, element_detail__allows_ssi=True).select_related(
        "element_detail", "element_detail__element", "element_detail__element__area", "ubication", "record_state"
    ).only(
        'element_detail__element__area_id',
        'element_detail__element__area__description',
        'element_detail__element_id',
        'element_detail__element__description',
        'element_detail__description',
        'record_state__description',
        'normalized_record_id',
        'created_at',
        'record_type_id',
        'start_date_process',
        'closing_date',
        'ubication',
    )
    serializer_class = RecordCardSSIPublicSerializer
    filterset_class = RecordCardPublicFilter
    pagination_class = IrisSSIPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        element_details_pks = ApplicationElementDetail.objects.get_elementdetailpks_byapp(self.request.application)
        return queryset.filter(element_detail_id__in=element_details_pks)


@method_decorator(name="get", decorator=public_iris_roles)
class RecordTypeListView(PublicApiListAPIView):
    """
    Endpoint to retrieve a list of record types
    """
    serializer_class = RecordTypePublicSerializer
    queryset = RecordType.objects.all()


@method_decorator(name="get", decorator=public_iris_roles)
class InputChannelListView(PublicApiListAPIView):
    """
    Endpoint to retrieve a list of input channels
    """
    serializer_class = InputChannelPublicSerializer
    queryset = InputChannel.objects.filter(visible=True)


@method_decorator(name="get", decorator=public_iris_roles)
class ApplicantTypeListView(PublicApiListAPIView):
    """
    Endpoint to retrieve a list of applicant types
    """
    serializer_class = ApplicantTypePublicSerializer
    queryset = ApplicantType.objects.all()


@method_decorator(name="post", decorator=public_iris_roles)
@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(
    request_body_serializer=RecordCardMobileCreatePublicSerializer, add_forbidden=False))
class RecordCardMobileCreateView(InternalOperatorMixin, ApplicantBlockedMixin, SetFeaturesMixin,
                                 SetBase64AttachmentsMixin, APIView):
    """
    Endpoint to create a RecordCard from xml_proxy/drupal apps.
    """

    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():

            record_card_serializer = RecordCardMobileCreatePublicSerializer(
                data=request.data, context=self.set_element_detail_context())

            if record_card_serializer.is_valid(raise_exception=True):
                record_data = record_card_serializer.validated_data
                if record_data.get("citizen"):
                    applicant = self.set_citizen_applicant(record_data["citizen"])
                else:
                    applicant = self.set_socialentity_applicant(record_data["social_entity"])

                element_detail = record_data.get("element_detail")
                applicant_blocked_response = self.check_applicant_blocked(applicant, element_detail)
                if applicant_blocked_response:
                    return applicant_blocked_response

                applicant_type = record_data.get("applicant_type")
                input_channel = record_data.get("input_channel")
                is_internal_operator = self.is_internal_operator(applicant, applicant_type.pk, input_channel.pk)
                if is_internal_operator and self.default_applicant:
                    applicant = self.default_applicant

                request = Request.objects.create(user_id=get_user_traceability_id(self.request.user),
                                                 applicant=applicant, applicant_type=applicant_type,
                                                 input_channel=input_channel, application=self.request.application,
                                                 normalized_id=set_reference(Request, "normalized_id"))

                ubication = self.set_ubication(record_data["ubication"]) if record_data.get("ubication") else None

                record_card = RecordCard.objects.create(
                    user_id="WEB", element_detail=element_detail,
                    support_id=Support.ALTRES_MITJANS, description=record_data["description"],
                    applicant_type=applicant_type, request=request, record_state_id=RecordState.PENDING_VALIDATE,
                    ubication=ubication, record_type=element_detail.record_type, input_channel=input_channel,
                    organization=record_data.get("organization", ""),
                    responsible_profile=Group.get_initial_group_for_record())
                if not ubication:
                    record_card.derivate(user_id="WEB", reason=Reason.INITIAL_ASSIGNATION)
                self.set_features(record_card, record_data.get("features", []))
                if self.request.data.get("record_card_response"):
                    record_card_response = self.set_record_card_response(record_card, is_internal_operator,
                                                                         element_detail.immediate_response)
                self.set_attachments(record_data.get("pictures", []), record_card)
                if record_card.record_can_be_autovalidated():
                    record_card.autovalidate_record('', self.request.user)
        record_card.send_record_card_created()
        if ubication:
            geocode_ubication.delay(ubication.pk, record_card.pk, user_id="WEB", reason=Reason.INITIAL_ASSIGNATION)
        if self.request.data.get("record_card_response"):
            save_last_applicant_response.delay(applicant.pk, record_card_response.pk)

        return Response(RecordCardMobileCreatedPublicSerializer(record_card).data, status=HTTP_201_CREATED)

    @staticmethod
    def set_ubication(location_data):
        ubication = Ubication()
        ubication.latitude = location_data.get("latitude", "")
        ubication.longitude = location_data.get("longitude", "")
        ubication.geocode_validation = location_data.get("geocode_validation", "")
        ubication.street = location_data.get("street", "")
        ubication.street2 = location_data.get("street2", "")
        ubication.floor = location_data.get("floor", "")
        ubication.stair = location_data.get("stair", "")
        ubication.door = location_data.get("door", "")
        ubication.district = location_data.get("district")
        ubication.neighborhood = location_data.get("neighborhood", "")
        ubication.neighborhood_b = location_data.get("neighborhood_b", "")
        ubication.neighborhood_id = location_data.get("neighborhood_id", "")
        ubication.save()
        logging.info(f'UBICATION WITH ADDRESS {ubication.street} FROM  {location_data.get("street", "")}')
        return ubication

    def set_element_detail_context(self):
        try:
            kwargs = ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy()
            kwargs["pk"] = self.request.data.get("element_detail_id")
            return {"element_detail": ElementDetail.objects.get(**kwargs)}
        except ElementDetail.DoesNotExist:
            return {}

    @staticmethod
    def set_citizen_applicant(citizen_data):
        try:
            citizen = Citizen.objects.get(dni=citizen_data.get("dni").upper())
        except Citizen.DoesNotExist:
            citizen = Citizen()
        except Citizen.MultipleObjectsReturned:
            citizen = Citizen.objects.filter(dni=citizen_data.get("dni").upper()).first()

        citizen.name = citizen_data.get("name")
        citizen.second_surname = citizen_data.get("second_surname")
        citizen.first_surname = citizen_data.get("first_surname")
        citizen.doc_type = citizen_data.get("doc_type")
        citizen.dni = citizen_data.get("dni")
        citizen.birth_year = citizen_data.get("birth_year")
        citizen.sex = citizen_data.get("sex", Citizen.UNKNOWN)
        citizen.district = citizen_data.get("district")
        citizen.language = citizen_data.get("language", SPANISH)
        citizen.save()

        applicant, _ = Applicant.objects.get_or_create(citizen=citizen)
        return applicant

    @staticmethod
    def set_socialentity_applicant(social_entity_data):
        try:
            social_entity = SocialEntity.objects.get(cif=social_entity_data.get("cif").upper())
        except SocialEntity.DoesNotExist:
            social_entity = SocialEntity()
        except SocialEntity.MultipleObjectsReturned:
            social_entity = SocialEntity.objects.filter(cif=social_entity_data.get("cif").upper()).first()

        social_entity.social_reason = social_entity_data.get("social_reason")
        social_entity.contact = social_entity_data.get("contact")
        social_entity.cif = social_entity_data.get("cif")
        social_entity.district = social_entity_data.get("district")
        social_entity.language = social_entity_data.get("language", SPANISH)
        social_entity.save()

        applicant, _ = Applicant.objects.get_or_create(social_entity=social_entity)
        return applicant

    def set_record_card_response(self, record_card, is_internal_operator, theme_immediate_response):
        response_data = self.request.data.get("record_card_response")
        response_data.update({"record_card_id": record_card.pk})
        response_serializer = RecordCardResponsePublicSerializer(data=response_data)
        if response_serializer.is_valid(raise_exception=True):
            response = response_serializer.save()
            if is_internal_operator:
                response.response_channel_id = ResponseChannel.NONE
                response.save()
            if theme_immediate_response:
                response.response_channel_id = ResponseChannel.IMMEDIATE
                response.save()
            return response


@method_decorator(name="get", decorator=public_iris_roles)
class FurniturePickUpView(PublicApiListAPIView):
    """
    List of furniture pickups. In addition to the pickup infomation, a text will be included with the instructions.
    List can be filtered by street code and number (together).
    """
    serializer_class = FurniturePickUpSerializer
    queryset = FurniturePickUp.objects.all()

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset()
        street_code = self.request.query_params.get("street_code")
        number = self.request.query_params.get("number")
        if street_code and number:
            queryset = queryset.filter(street_code=street_code, number=number)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        furnitures_shedule_range = Parameter.get_parameter_by_key("RECOLLIDA_MOBLES_HORARIS", "20:00 a 22:00 h")
        furnitures_shedule_from = Parameter.get_parameter_by_key("RECOLLIDA_MOBLES_HORA", "20:00")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
        result = serializer.data
        if not queryset:
            result["TEXT"] = _("En aquest adreça la recollida es fa a través de contenidors."
                               " Consulteu la ubicació al telèfon del civisme 900 226 226 (trucada gratuita)")
            return Response(result)
        else:
            for json_dict in result["results"]:
                json_dict["service_description"] = self.days_traduction(json_dict["service_description"])
                if json_dict["service_type"] == "V":
                    json_dict["TEXT"] = _("Podeu deixar els mobles vells davant de la porteria el {}"
                                          " de {}").format(json_dict["service_description"], furnitures_shedule_range)
                elif json_dict["service_type"] == "D":
                    json_dict["TEXT"] = _("Cal trucar al telèfon gratuït del Civisme 900 226 226 per sol·licitar"
                                          " la recollida dels mobles i baixar-los els {}, a partir de les {} hores."
                                          " La recollida es fará a l'endemà però nomès retiraran els mobles i trastos"
                                          " que s'hagin demanat a través d'aquest"
                                          " servei").format(json_dict["service_description"], furnitures_shedule_from)
        return Response(result)

    def days_traduction(self, day):
        if day == "DILLUNS":
            day = _("DILLUNS")
        elif day == "DIMARTS":
            day = _("DIMARTS")
        elif day == "DIMECRES":
            day = _("DIMECRES")
        elif day == "DIJOUS":
            day = _("DIJOUS")
        elif day == "DIVENDRES":
            day = _("DIVENDRES")
        elif day == "DISSABTE":
            day = _("DISSABTE")
        elif day == "DIUMENGE":
            day = _("DIUMENGE")
        return day


@method_decorator(name="post", decorator=public_iris_roles)
@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(
    request_body_serializer=MessageShortHashSerializer,
    responses={
        HTTP_201_CREATED: MessageHashCreateSerializer,
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_404_NOT_FOUND: "Message to response not found",
        HTTP_409_CONFLICT: "Message previously answered"
    }
))
class MessageHashCreateView(SetFilesMixin, CreateAPIView):
    """
    Endpoint to create a message as the answer of a communication send from the IRIS2 backoffice.
    """

    serializer_class = MessageHashCreateSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        try:
            previous_message = Message.objects.select_related("conversation", "conversation__record_card").get(
                hash=self.kwargs["hash"], conversation__type__in=Conversation.HASH_TYPES)
        except Message.DoesNotExist:
            raise Http404(_("No Message matches the given query."))

        if previous_message.is_answered:
            return Response(_("The messages was previously answered"), status=HTTP_409_CONFLICT)

        serializer_data = {}
        if "body" in request.data:
            serializer_data.update(json.loads(request.data.get("body")))
        else:
            serializer_data.update(request.data)

        serializer_data["conversation_id"] = previous_message.conversation_id
        serializer_data["record_state_id"] = previous_message.conversation.record_card.record_state_id

        files = [{"filename": file.name, "file": file} for _, file in request.FILES.items()]
        serializer_data.update({"attachments": files})

        serializer = self.get_serializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Previous messages has been answered
        previous_message.is_answered = True
        previous_message.save()

        self.set_files(serializer_data.get("attachments", []), previous_message.conversation.record_card)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)


class MessageHashDetailView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RecordCardMinimalPublicSerializer

    def get_object(self) -> RecordCard:
        hash = self.kwargs["hash"]
        return get_object_or_404(RecordCard, conversation__message__hash=hash)


class ParametersMixin:
    serializer_class = ParameterPublicSerializer
    extra_ate_parameters = ["CERCA_MINIM_PARAULA", "CERCA_SUBSTRING"]

    def get_queryset(self):
        return Parameter.objects.filter(Q(category=Parameter.WEB) | Q(parameter__in=self.extra_ate_parameters),
                                        show=True, visible=True)


@method_decorator(name="get", decorator=public_iris_roles)
class ParameterListATEVisibleView(ParametersMixin, PublicApiListAPIView):
    """
    Endpoint to retrieve a list of parameters
    """
    pass


@method_decorator(name="get", decorator=public_iris_roles)
class ParameterDetailATEVisibleView(ParametersMixin, RetrieveAPIView):
    """
    Endpoint to retrieve the detail of a parameter
    """
    permission_classes = (AllowAny,)
    lookup_url_kwarg = "parameter"
    lookup_field = "parameter"


@method_decorator(name="get", decorator=public_iris_roles)
@method_decorator(name="get", decorator=swagger_auto_schema(responses={
    HTTP_200_OK: "Mario details",
    HTTP_404_NOT_FOUND: "Details not found at Mario",
}))
class MarioView(APIView):
    """
    Endpoint that works as a proxy between the ATE ElementDetail search and the Mario Service. If the number of words
    if lower than the parameter MARIO_PARAULES_CERCA_KEYWORDS , the search is done by keywords.
    """
    filterset_class = MarioPublicFilter
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):

        theme_param = self.request.GET.get("tematica")
        if not theme_param:
            return Response("Set tematica GET param", status=HTTP_404_NOT_FOUND)

        max_numwords_keyword_search = int(Parameter.get_parameter_by_key("MARIO_PARAULES_CERCA_KEYWORDS", 4))
        search_terms = theme_param.split()
        if len(search_terms) < max_numwords_keyword_search or not settings.MARIO_ENABLED:
            return self.keywords_search(search_terms, theme_param.lower())

        return self.mario_service_search(theme_param)

    def keywords_search(self, search_terms, theme_param):
        details_ids, keyword_details_ids = KeywordSearch(search_terms).details_search()
        details = self.get_details_information(details_ids)
        return Response(self.prepare_details_info(theme_param, details, keyword_details_ids), status=HTTP_200_OK)

    @staticmethod
    def get_details_information(details_ids):
        active_date_filters = Q(activation_date__lte=timezone.now().date()) | Q(activation_date__isnull=True)
        visible_date_filters = Q(visible_date__lte=timezone.now().date()) | Q(visible_date__isnull=True)
        return ElementDetail.objects.filter(active_date_filters, visible_date_filters, pk__in=details_ids,
                                            active=True, visible=True).values("id", "description", "element_id",
                                                                              "element__description",
                                                                              "record_type__description_ca")

    def prepare_details_info(self, theme_param, details, keyword_details_ids):
        elements_dict = {}
        for detail in details:
            element_id = detail["element_id"]
            if element_id not in elements_dict:
                elements_dict[element_id] = self.set_keyword_initial_element(theme_param, element_id,
                                                                             detail["element__description"])
            elements_dict[element_id]["details"].append(self.set_keyword_detail(detail))
            if detail["id"] in keyword_details_ids:
                elements_dict[element_id]["probability"] = 1

        count = len(elements_dict.keys())
        elements_list = []
        for key, element_dict in elements_dict.items():
            element_dict.update({"count": count})
            elements_list.append(element_dict)

        elements_list.sort(reverse=True, key=lambda x: x["probability"])
        return elements_list

    @staticmethod
    def set_keyword_initial_element(theme_param, element_id, element_description):
        return {
            "question": theme_param,
            "element_id": element_id,
            "element_name": element_description,
            "details": [],
            "is_correct": None,
            "detail_id": 0,
            "probability": 0.7,
            "pk": 0,
        }

    @staticmethod
    def set_keyword_detail(detail):
        return {
            "description_id": detail["id"],
            "description": detail["description"],
            "record_type": detail["record_type__description_ca"]
        }

    def mario_service_search(self, theme_param):
        mario_response = MarioService().search(theme_param)
        if mario_response.status_code != HTTP_200_OK:
            logger.error('MARIO | ERROR | {} | SEARCH {} | {} |'.format(
                mario_response.status_code, theme_param, mario_response.text
            ))
            return Response(mario_response.json(), status=mario_response.status_code)

        mario_response = mario_response.json()
        mario_detail_ids, mario_elements_ids = self.get_mario_ids(mario_response)

        current_lang = translation.get_language()

        available_detail_ids = self.get_available_details_ids(mario_detail_ids, current_lang)
        element_descriptions = self.get_elements_descriptions(mario_elements_ids, current_lang)

        return Response(self.set_service_response(mario_response, available_detail_ids, element_descriptions),
                        status=HTTP_200_OK)

    @staticmethod
    def get_mario_ids(mario_response):
        details_ids = []
        elements_ids = []
        for mario_object in mario_response:
            details_ids += [detail["description_id"] for detail in mario_object.get("details", [])
                            if "description_id" in detail]
            elements_ids.append(mario_object["element_id"])
        return details_ids, elements_ids

    def get_available_details_ids(self, mario_details_ids, current_lang):
        applications_pks = [self.request.application, Application.WEB_DIRECTO, Application.CONSULTES_DIRECTO]
        element_details_pks = ApplicationElementDetail.objects.get_elementdetailpks_multiple_apps(applications_pks)

        active_date_filters = Q(activation_date__lte=timezone.now().date()) | Q(activation_date__isnull=True)
        visible_date_filters = Q(visible_date__lte=timezone.now().date()) | Q(visible_date__isnull=True)

        description = "description_{}".format(current_lang)

        queryset = ElementDetail.objects.filter(pk__in=element_details_pks)
        queryset = queryset.filter(active_date_filters, visible_date_filters, pk__in=mario_details_ids,
                                   active=True, visible=True).values("id", description)

        return {detail["id"]: detail[description] for detail in queryset}

    @staticmethod
    def get_elements_descriptions(mario_elements_ids, current_lang):
        description = "description_{}".format(current_lang)
        queryset = Element.objects.filter(pk__in=mario_elements_ids).values("id", description)
        return {element["id"]: element[description] for element in queryset}

    @staticmethod
    def set_service_response(mario_response, available_detail_ids, element_descriptions):
        service_response = []
        for mario_object in mario_response:
            mario_dict = mario_object.copy()
            details = mario_dict.get("details", [])
            mario_dict["details"] = []

            for detail in details:
                if detail["description_id"] in available_detail_ids:
                    detail["description"] = available_detail_ids[detail["description_id"]]
                    mario_dict["details"].append(detail)

            if mario_dict["details"]:
                mario_dict["element_name"] = element_descriptions[mario_dict["element_id"]]
                service_response.append(mario_dict)
        return service_response
