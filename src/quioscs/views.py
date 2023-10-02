from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView

from iris_masters.models import ApplicantType, InputChannel, RecordState, Support, ResponseChannel, Reason
from iris_masters.views import BasicMasterListApiView
from main.api.schemas import create_swagger_auto_schema_factory
from profiles.models import Group
from public_api.views import SetBase64AttachmentsMixin, SetFeaturesMixin, ApplicantBlockedMixin
from quioscs.serializers import (ElementDetailQuioscsSerializer, RecordCardCreateQuioscsSerializer,
                                 RecordCardQuioscSerializer)
from record_cards.models import Citizen, Applicant, Request, Ubication, RecordCard, RecordCardResponse
from record_cards.record_actions.normalized_reference import set_reference
from record_cards.tasks import geocode_ubication, save_last_applicant_response
from themes.filters import ElementDetailFilter
from themes.models import ElementDetail
from themes.views import ElementDetailQuerySetMixin, BasicOrderingFieldsSearchMixin


class ElementDetailSearchView(ElementDetailQuerySetMixin, BasicOrderingFieldsSearchMixin, BasicMasterListApiView):
    """
    Endpoint to search themes
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be filtered by area, element, applications, record_types, keywords, active, activation_date_ini,
      activation_date_end
     - can be ordered by description
    """

    serializer_class = ElementDetailQuioscsSerializer
    filterset_class = ElementDetailFilter
    ordering_fields = BasicOrderingFieldsSearchMixin.ordering_fields.append('description')


class ElementDetailRetrieveView(ElementDetailQuerySetMixin, RetrieveAPIView):
    """
    Endpoint to retrieve the detail of a theme
    """
    serializer_class = ElementDetailQuioscsSerializer


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(
    request_body_serializer=RecordCardQuioscSerializer, add_forbidden=False))
class RecordCardCreateView(ApplicantBlockedMixin, SetFeaturesMixin, SetBase64AttachmentsMixin, APIView):
    """
    Endpoint to create a RecordCard for the service of Quiosc, with the availibity of sending attached files in base64.
    The input_channel is always QUIOSC. The response of the RecordCard is by email or it does not have to be answered.
    The user has to be authenticated.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):

        with transaction.atomic():
            record_card_create_serializer = RecordCardCreateQuioscsSerializer(data=request.data,
                                                                              context=self.set_element_detail_context())

            if record_card_create_serializer.is_valid(raise_exception=True):
                record_data = record_card_create_serializer.validated_data

                applicant = self.set_citizen_applicant(record_data)

                element_detail = record_data["element_detail_id"]
                applicant_blocked_response = self.check_applicant_blocked(applicant, element_detail)
                if applicant_blocked_response:
                    return applicant_blocked_response

                applicant_type_id = ApplicantType.CIUTADA
                application = self.request.application if hasattr(self.request, "application") else None

                user_id = "QUIOSCS"

                db_request = Request.objects.create(
                    user_id=user_id, applicant=applicant, application=application, applicant_type_id=applicant_type_id,
                    input_channel_id=InputChannel.QUIOSC, normalized_id=set_reference(Request, "normalized_id"))

                ubication = self.set_ubication(record_data["location"]) if record_data.get("location") else None

                record_card = RecordCard.objects.create(
                    user_id=user_id, element_detail=element_detail, request=db_request,
                    support_id=Support.ALTRES_MITJANS, description=record_data["description"],
                    applicant_type_id=applicant_type_id,
                    record_state_id=RecordState.PENDING_VALIDATE, ubication=ubication,
                    input_channel_id=InputChannel.QUIOSC, organization=user_id,
                    responsible_profile=Group.get_initial_group_for_record()
                )

                self.set_features(record_card, record_data.get("features", []))
                record_card_response = self.set_record_card_response(record_data, record_card)
                self.set_attachments(record_data.get("pictures", []), record_card)
                if not ubication:
                    record_card.derivate(user_id=user_id, reason=Reason.INITIAL_ASSIGNATION)
                if record_card.record_can_be_autovalidated():
                    record_card.autovalidate_record('', self.request.user)

        record_card.send_record_card_created()
        if ubication:
            geocode_ubication.delay(ubication.pk, record_card.pk, user_id="WEB", reason=Reason.INITIAL_ASSIGNATION)
        save_last_applicant_response.delay(applicant.pk, record_card_response.pk)

        return Response(RecordCardQuioscSerializer(record_card).data, status=HTTP_201_CREATED)

    def set_element_detail_context(self):
        try:
            kwargs = ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy()
            kwargs["pk"] = self.request.data.get("element_detail_id")
            return {"element_detail": ElementDetail.objects.get(**kwargs)}
        except ElementDetail.DoesNotExist:
            return {}

    @staticmethod
    def set_citizen_applicant(record_data):
        dni = record_data.get("document").upper()
        doc_type = record_data.get("document_type")
        email = record_data.get("email")
        try:
            citizen = Citizen.objects.get(dni=dni, doc_type=doc_type)
        except Citizen.DoesNotExist:
            name = email if email else dni
            citizen = Citizen.objects.create(name=name, first_surname=name, dni=dni, doc_type=doc_type)
        except Citizen.MultipleObjectsReturned:
            citizen = Citizen.objects.filter(dni=dni, doc_type=doc_type).first()
        try:
            return Applicant.objects.get(citizen_id=citizen.pk)
        except Applicant.DoesNotExist:
            return Applicant.objects.create(citizen=citizen)

    @staticmethod
    def set_ubication(location_data):
        return Ubication.objects.create(via_type=location_data["via_type"], district=location_data["district"],
                                        geocode_district_id=location_data["geocode"],
                                        street=location_data["street"], street2=location_data["number"])

    @staticmethod
    def set_record_card_response(record_data, record_card):
        email = record_data.get("email")
        if email:
            address_mobile_email = email
            response_channel = ResponseChannel.EMAIL
        else:
            address_mobile_email = ""
            response_channel = ResponseChannel.NONE
        return RecordCardResponse.objects.create(response_channel_id=response_channel, record_card_id=record_card.pk,
                                                 address_mobile_email=address_mobile_email)
