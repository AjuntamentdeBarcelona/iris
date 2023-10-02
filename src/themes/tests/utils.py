from datetime import timedelta

from django.utils import timezone
from model_mommy import mommy

from iris_masters.models import RecordType, Process, District, RecordState, ResponseChannel
from profiles.tests.utils import create_groups
from themes.models import Area, Element, ElementDetail, DerivationDirect, DerivationDistrict, \
    ElementDetailResponseChannel


class CreateThemesMixin:

    def create_area(self, user_id=None):
        if not user_id:
            user_id = "222"
        return mommy.make(Area, user_id=user_id, deleted=None)

    def create_element(self, user_id=None, area=None, is_favorite=False):
        if not user_id:
            user_id = "222"
        if not area:
            area = self.create_area(user_id=user_id)
        return mommy.make(Element, user_id=user_id, area=area, is_favorite=is_favorite, deleted=None)

    def create_element_detail(self, user_id=None, element=None, record_type_id=None, process_id=Process.CLOSED_DIRECTLY,
                              description="test", short_description="test", similarity_hours=None, allows_ssi=False,
                              similarity_meters=None, autovalidate_records=False, requires_appointment=False,
                              validated_reassignable=False, immediate_response=False, external_protocol_id="22222",
                              create_direct_derivations=False, create_district_derivations=False,
                              validation_place_days=None, active=True, fill_active_mandatory_fields=True, sla_hours=72,
                              set_future_activation_date=False, visible=True, set_future_visible_date=False,
                              requires_citizen=False, requires_ubication=False, requires_ubication_district=False,
                              aggrupation_first=False, allow_multiderivation_on_reassignment=False,
                              add_response_channels=True, detail_code='010101', element_detail_id=None):
        if not user_id:
            user_id = "222"
        if not element:
            element = self.create_element()
        if not record_type_id:
            record_type_id = mommy.make(RecordType, user_id=user_id).pk
        if element_detail_id:
            element_detail = mommy.make(
                ElementDetail, id=element_detail_id,
                user_id=user_id, element=element, record_type_id=record_type_id, deleted=None,
                short_description=short_description, short_description_es=short_description, process_id=process_id,
                short_description_gl=short_description, short_description_en=short_description, description=description,
                description_es=description, description_gl=description, description_en=description,
                allows_ssi=allows_ssi, similarity_hours=similarity_hours, autovalidate_records=autovalidate_records,
                active=active, similarity_meters=similarity_meters, immediate_response=immediate_response,
                requires_appointment=requires_appointment, validated_reassignable=validated_reassignable,
                external_protocol_id=external_protocol_id, visible=visible, requires_citizen=requires_citizen,
                requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district,
                aggrupation_first=aggrupation_first, sla_hours=sla_hours, detail_code=detail_code,
                allow_multiderivation_on_reassignment=allow_multiderivation_on_reassignment, footer_text='1')
        else:
            element_detail = mommy.make(
                ElementDetail,
                user_id=user_id, element=element, record_type_id=record_type_id, deleted=None,
                short_description=short_description, short_description_es=short_description, process_id=process_id,
                short_description_gl=short_description, short_description_en=short_description, description=description,
                description_es=description, description_gl=description, description_en=description,
                allows_ssi=allows_ssi, similarity_hours=similarity_hours, autovalidate_records=autovalidate_records,
                active=active, similarity_meters=similarity_meters, immediate_response=immediate_response,
                requires_appointment=requires_appointment, validated_reassignable=validated_reassignable,
                external_protocol_id=external_protocol_id, visible=visible, requires_citizen=requires_citizen,
                requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district,
                aggrupation_first=aggrupation_first, sla_hours=sla_hours, detail_code=detail_code,
                allow_multiderivation_on_reassignment=allow_multiderivation_on_reassignment, footer_text='1')

        if fill_active_mandatory_fields:
            element_detail.app_description_en = description
            element_detail.app_description_es = description
            element_detail.app_description_gl = description
            element_detail.pda_description = description
            element_detail.rat_code = description
            element_detail.similarity_hours = 15
            element_detail.similarity_meters = 1500
            element_detail.app_resolution_radius_meters = 56
            element_detail.sla_hours = sla_hours

        if set_future_activation_date:
            element_detail.activation_date = timezone.now().date() + timedelta(days=5)
        else:
            element_detail.activation_date = timezone.now().date()
        if set_future_visible_date:
            element_detail.visible_date = timezone.now().date() + timedelta(days=5)
        else:
            element_detail.visible_date = timezone.now().date()

        if create_direct_derivations or create_district_derivations:
            self.create_derivations(element_detail, create_direct_derivations, create_district_derivations)

        if validation_place_days:
            element_detail.validation_place_days = validation_place_days

        if add_response_channels:
            self.add_response_channels(element_detail)

        element_detail.save()
        return element_detail

    @staticmethod
    def add_response_channels(element_detail):
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=ResponseChannel.SMS)
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=ResponseChannel.EMAIL)

    @staticmethod
    def create_derivations(element_detail, create_direct_derivations, create_district_derivations):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        if create_direct_derivations:
            DerivationDirect.objects.create(element_detail=element_detail, group=grand_parent,
                                            record_state_id=RecordState.PENDING_VALIDATE)
            DerivationDirect.objects.create(element_detail=element_detail, group=grand_parent,
                                            record_state_id=RecordState.CLOSED)
            DerivationDirect.objects.create(element_detail=element_detail, group=parent,
                                            record_state_id=RecordState.IN_RESOLUTION)
            DerivationDirect.objects.create(element_detail=element_detail, group=first_soon,
                                            record_state_id=RecordState.CANCELLED)
            DerivationDirect.objects.create(element_detail=element_detail, group=noambit_soon,
                                            record_state_id=RecordState.EXTERNAL_PROCESSING)

        if create_district_derivations:
            for district in District.objects.filter(allow_derivation=True):
                DerivationDistrict.objects.create(element_detail=element_detail, district=district, group=second_soon,
                                                  record_state_id=RecordState.PENDING_VALIDATE)
