import hashlib
import logging
import os
from copy import deepcopy
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import Q
from drf_chunked_upload.models import ChunkedUpload
from drf_chunked_upload.settings import COMPLETE_EXT, INCOMPLETE_EXT
from geopy.distance import distance
from utm import to_latlon, from_latlon

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.dispatch import Signal

from custom_safedelete.models import CustomSafeDeleteModel
from features.models import Feature, Values
from iris_masters.models import (ApplicantType, Application, CommunicationMedia, InputChannel, Process, Reason,
                                 RecordState, RecordType, ResponseChannel, Support, UserTrack, District, ResolutionType,
                                 Parameter, UserIdField)

from main.api.validators import MaxYearValidator
from main.utils import LANGUAGES, get_default_lang, ENGLISH, SPANISH, get_user_traceability_id
from iris_masters.mixins import CleanEnabledBase, CleanSafeDeleteBase
from profiles.models import Group
from profiles.permissions import IrisPermissionChecker
from profiles.tasks import send_allocated_notification
from record_cards.anonymize.citizen_anonymize import CitizenAnonymize
from record_cards.managers import RecordCardReasignationManager, RecordFileManager, RecordCardQueryset
from record_cards.permissions import RECARD_COORDINATOR_VALIDATION_DAYS, RECARD_VALIDATE_OUTAMBIT
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.record_actions.derivations import derivate
from record_cards.record_actions.external_validators import get_external_validator
from record_cards.record_actions.normalized_reference import set_reference, generate_next_reference
from record_cards.record_actions.reasignations import PossibleReassignations
from record_cards.record_actions.state_machine import RecordCardStateMachine
from themes.models import ElementDetail

record_card_created = Signal(providing_args=["record_card"])
record_card_state_changed = Signal(providing_args=["record_card"])
record_card_directly_closed = Signal(providing_args=["record_card"])
record_card_resend_answer = Signal(providing_args=["record_card"])

logger = logging.getLogger(__name__)


class Ubication(UserTrack):
    """
    IRS_TB_UBICACIO
    """
    via_type = models.CharField(_(u"Via Type"), max_length=35, blank=True)
    official_street_name = models.CharField(_(u"Official Street Name"), max_length=120, blank=True, db_index=True)
    street = models.CharField(_(u"Street"), max_length=120, blank=True, db_index=True)
    street2 = models.CharField(_(u"Street 2"), max_length=60, blank=True, db_index=True)
    numFi = models.CharField(_(u"NumFi"), max_length=60, blank=True, db_index=True, null=True)

    nexus = models.BooleanField(_(u"Nexus"), default=False)

    neighborhood = models.CharField(_(u"Neighborhood"), max_length=80, blank=True, db_index=True)
    neighborhood_b = models.CharField(_(u"Neighborhood B"), max_length=80, blank=True)
    neighborhood_id = models.CharField(_(u"Neighborhood ID"), max_length=10, blank=True)
    district = models.ForeignKey(District, verbose_name=_(u"District"), on_delete=models.PROTECT, null=True, blank=True,
                                 db_index=True)
    statistical_sector = models.CharField(_(u"Statistical Sector"), max_length=80, blank=True)

    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    geocode_validation = models.CharField(_(u"Geocode Validation"), max_length=60, blank=True)
    geocode_district_id = models.CharField(_(u"Geocodeo District ID"), max_length=10, blank=True)
    research_zone = models.CharField(_(u"Research Zone"), max_length=10, blank=True)

    stair = models.CharField(_(u"Stair"), max_length=20, blank=True)
    floor = models.CharField(_(u"Floor"), max_length=20, blank=True)
    door = models.CharField(_(u"Door"), max_length=20, blank=True)
    letter = models.CharField(_(u"Letter"), max_length=3, blank=True)
    letterFi = models.CharField(_(u"LetterFi"), max_length=3, blank=True, null=True)

    coordinate_x = models.FloatField(_(u"Coordinate X"), null=True, blank=True)
    coordinate_y = models.FloatField(_(u"Coordinate Y"), null=True, blank=True)
    coordinate_utm_x = models.FloatField(_(u"Coordinate UTM X"), null=True, blank=True)
    coordinate_utm_y = models.FloatField(_(u"Coordinate UTM Y"), null=True, blank=True)
    latitude = models.CharField(_(u"Latitude"), max_length=20, blank=True, null=True)
    longitude = models.CharField(_(u"Longitude"), max_length=20, blank=True, null=True)
    xetrs89a = models.FloatField(_(u"Xetrs89a"), null=True, blank=True)
    yetrs89a = models.FloatField(_(u"Yetrs89a"), null=True, blank=True)

    numbering_type = models.CharField(_(u"Numbering type"), max_length=60, blank=True)

    temp_error = models.TextField(_(u"Temp error"), blank=True)
    polygon_code = models.CharField(_("Polygon Code"), max_length=100, blank=True)

    def __str__(self):
        return self.short_address

    @cached_property
    def short_address(self):
        if self.via_type and self.street:
            return "{} {} {}".format(self.via_type, self.street, self.street2)
        elif self.district:
            return _("District: {}").format(self.district.name)
        return ""

    def has_coordinates(self):
        return self.xetrs89a or self.latitude

    def adjust_coordinates(self):
        if self.xetrs89a and not self.latitude:
            self.latitude, self.longitude = self.etrs_to_latlon
        elif not self.xetrs89a and self.latitude:
            self.xetrs89a, self.yetrs89a = from_latlon(
                float(self.latitude), float(self.longitude), settings.GEO_UTM_ZONE
            )[:2]

    @cached_property
    def etrs_to_latlon(self):
        if not self.xetrs89a or not self.yetrs89a:
            return None
        return to_latlon(self.xetrs89a, self.yetrs89a, settings.GEO_UTM_ZONE, "T")

    def distance(self, distance_ubication):
        """
        :param distance_ubication: Ubication to calculate distance
        :return: Distance between self ubication and another in meters
        """
        if not self.etrs_to_latlon or not distance_ubication.etrs_to_latlon:
            return None
        return distance(self.etrs_to_latlon, distance_ubication.etrs_to_latlon).meters

    def is_different_location(self, other):
        return self.district_id != other.district_id \
               or self.xetrs89a != other.xetrs89a \
               or self.yetrs89a != other.yetrs89a

    def is_empty(self):
        return not self.district_id and not self.street


class ExtendedGeocodeUbication(UserTrack):
    ubication = models.OneToOneField(Ubication, verbose_name=_("Ubication"), on_delete=models.CASCADE)
    llepost_f = models.CharField(_(u"Letter post f"), max_length=3, blank=True)
    numpost_f = models.CharField(_(u"Num post f"), max_length=60, blank=True)
    dist_post = models.CharField(_(u"Dist post"), max_length=60, blank=True)
    codi_illa = models.CharField(_(u"Codi illa"), max_length=60, blank=True)
    solar = models.CharField(_(u"Solar"), max_length=60, blank=True)
    codi_parc = models.CharField(_(u"Codi parc"), max_length=60, blank=True)

    def __str__(self):
        return "Geocoder - {}".format(self.ubication.short_address)


class ApplicantData:
    """
    Base class for applicant data models. It defines the common required attributes.
    """

    @property
    def legal_id(self):
        return ""

    def _copy_from(self, from_instance, copy_attrs):
        if not self.created_at:
            self.created_at = from_instance.created_at
        for attr in copy_attrs:
            if getattr(from_instance, attr, None):
                setattr(self, attr, getattr(from_instance, attr, None))
        return self

    @property
    def full_name(self):
        return ""


class Citizen(ApplicantData, CleanSafeDeleteBase, CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_CIUTADA
    """
    field_error_name = "dni"

    MALE = "m"
    FEMALE = "f"
    UNKNOWN = "u"

    SEXES = (
        (MALE, _("Male")),
        (FEMALE, _("Female")),
        (UNKNOWN, _("Unknown")),
    )

    NIF = 0
    NIE = 1
    PASS = 2

    DOC_TYPES = (
        (NIF, _("NIF")),
        (NIE, _("NIE")),
        (PASS, _("PASS"))
    )

    CITIZEN_CHOICE = 1

    name = models.CharField(_(u"Name"), max_length=60, db_index=True)
    first_surname = models.CharField(_(u"First Surname"), max_length=60, db_index=True)
    second_surname = models.CharField(_(u"Second Surname"), max_length=60, blank=True, db_index=True)
    full_normalized_name = models.CharField(_(u"Full normal name"), max_length=120, blank=True, db_index=True)
    normalized_name = models.CharField(_(u"Normalized Name"), max_length=60, blank=True)
    normalized_first_surname = models.CharField(_(u"Normalized First Surname"), max_length=60, blank=True)
    normalized_second_surname = models.CharField(_(u"Normalized Second Surname"), max_length=60, blank=True)

    dni = models.CharField(_(u"DNI"), max_length=15, db_index=True)
    birth_year = models.SmallIntegerField(_(u"Birth Year"), blank=True, null=True,
                                          validators=[MinValueValidator(1900), MaxYearValidator()])
    sex = models.CharField(_("Sex"), max_length=1, choices=SEXES, default=UNKNOWN)
    language = models.CharField(_("Language"), max_length=2, choices=LANGUAGES, default=SPANISH)
    response = models.BooleanField(_(u"Response"), default=False)

    district = models.ForeignKey(District, verbose_name=_(u"District"), on_delete=models.PROTECT, null=True, blank=True)
    doc_type = models.PositiveSmallIntegerField(_(u"Document Type"), default=NIF, choices=DOC_TYPES)
    mib_code = models.PositiveIntegerField(_(u"MIB Code"), null=True)
    blocked = models.BooleanField(_(u"Blocked"), default=False)

    def __str__(self):
        return "{} {}".format(self.name, self.first_surname)

    @property
    def legal_id(self):
        return self.dni.upper()

    @property
    def full_name(self):
        return "{} {} {}".format(self.name, self.first_surname, self.second_surname)

    @staticmethod
    def check_no_repeat_dni(dni, citizen_pk):
        if Applicant.is_nd_doc(dni):
            if not settings.CITIZEN_ND_ENABLED:
                raise ValidationError({"dni": _("Citizen ND logic is not enabled, couldn't check for existing dni")})
        else:
            citizen_queryset = Citizen.objects.filter(dni__iexact=dni).values("dni")
            if citizen_pk and citizen_queryset.exclude(pk=citizen_pk):
                raise ValidationError({"dni": _("The inserted dni was previously assigned to another citizen")})
            elif not citizen_pk and citizen_queryset:
                raise ValidationError({"dni": _("The inserted dni was previously assigned to another citizen")})

    def clean(self):
        super().clean()
        self.check_no_repeat_dni(self.dni, self.pk)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"dni": self.dni}

    def save(self, keep_deleted=False, **kwargs):
        self.dni = self.dni.upper()
        super().save(keep_deleted=keep_deleted, **kwargs)

    def copy_from(self, from_applicant):
        return self._copy_from(from_applicant, copy_attrs=[
            "id", "first_surname", "second_surname", "name", "normalized_name", "normalized_first_surname",
            "normalized_second_surname", "blocked", "dni", "birth_year", "sex", "language", "district", "mib_code",
            "blocked", "response"])

    @property
    def can_be_anonymized(self):
        applicant_ids = self.applicant_set.all().values_list("id", flat=True)
        return not RecordCard.objects.applicants_open_records(applicant_ids)


class SocialEntity(ApplicantData, CleanSafeDeleteBase, CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_AGRUPACIO
    """
    SOCIAL_ENTITY_CHOICE = 2

    field_error_name = "cif"

    social_reason = models.CharField(_(u"Social Reason"), max_length=60, db_index=True)
    normal_social_reason = models.CharField(_(u"Normal Social Reason"), max_length=60, blank=True)
    contact = models.CharField(_(u"Contact"), max_length=120)

    cif = models.CharField(_(u"CIF"), max_length=15, db_index=True)
    language = models.CharField(_("Language"), max_length=2, choices=LANGUAGES, default=SPANISH)
    response = models.BooleanField(_(u"Response"), default=False)

    district = models.ForeignKey(District, verbose_name=_(u"District"), on_delete=models.PROTECT, null=True, blank=True)
    mib_code = models.PositiveIntegerField(_(u"MIB Code"), null=True)
    blocked = models.BooleanField(_(u"Blocked"), default=False)

    def __str__(self):
        return "{} - {}".format(self.social_reason, self.cif)

    @property
    def legal_id(self):
        return self.cif.upper()

    @property
    def full_name(self):
        return self.social_reason

    def save(self, keep_deleted=False, **kwargs):
        self.cif = self.cif.upper()
        super().save(keep_deleted=keep_deleted, **kwargs)

    @staticmethod
    def check_no_repeat_cif(cif, social_entity_pk):
        social_entity = SocialEntity.objects.filter(cif__iexact=cif).values("cif")
        if social_entity_pk and social_entity.exclude(pk=social_entity_pk):
            raise ValidationError({"cif": _("The inserted cif was previously assigned to another social_entity")})
        elif not social_entity_pk and social_entity:
            raise ValidationError({"cif": _("The inserted cif was previously assigned to another social_entity")})

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"cif": self.cif}

    def copy_from(self, from_applicant):
        return self._copy_from(from_applicant, copy_attrs=["id", "social_reason", "normal_social_reason", "contact",
                                                           "language", "mib_code", "district", "blocked"])


class InternalOperator(CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_MA_OPERADORS_INTERNS (xaloc)
    """
    document = models.CharField(_(u"Internal operator document"), max_length=15, db_index=True)
    applicant_type = models.ForeignKey(ApplicantType, verbose_name=_(u"Applicant Type"), on_delete=models.PROTECT)
    input_channel = models.ForeignKey(InputChannel, verbose_name=_(u"Input Channel"), on_delete=models.PROTECT)

    def __str__(self):
        return "Internal Operator: {}".format(self.document)

    class Meta:
        unique_together = ("document", "applicant_type", "input_channel")
        ordering = ("document",)

    @property
    def can_be_deleted(self):
        return True


class Applicant(CleanSafeDeleteBase, CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_SOLICITANT
    """
    field_error_name = "citizen"

    citizen = models.ForeignKey(Citizen, verbose_name=_(u"Citizen"), null=True, blank=True, on_delete=models.PROTECT)
    social_entity = models.ForeignKey(SocialEntity, verbose_name=_(u"Social Entity"), null=True, blank=True,
                                      on_delete=models.PROTECT)
    flag_ca = models.BooleanField(_(u"Flag CA"), default=True)
    pend_anonymize = models.BooleanField(_(u"Pend to anonymize"), default=False)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"citizen": self.citizen, "social_entity": self.social_entity}

    def __str__(self):
        if self.citizen_id:
            return self.citizen.__str__()
        return self.social_entity.__str__()

    @staticmethod
    def check_citizen_social_entity_assignation(citizen, social_entity):
        if not citizen and not social_entity:
            error_text = _(u"Citizen and Social Entity can not be null at the same time. Please set a value "
                           u"for one or the other.")
            raise ValidationError({"citizen": error_text, "social_entity": error_text})
        if citizen and social_entity:
            error_text = _(u"Citizen and Social Entity can not be set at the same time. Please deselect "
                           u"one or the other.")
            raise ValidationError({"citizen": error_text, "social_entity": error_text})

    @property
    def info(self):
        return self.citizen if getattr(self, "citizen", None) else self.social_entity

    @property
    def language(self):
        return self.info.language

    @property
    def full_name(self):
        return self.info.full_name

    @cached_property
    def origin(self):
        return None

    @property
    def document(self):
        return self.info.legal_id

    @property
    def blocked(self):
        return self.info.blocked

    @staticmethod
    def is_nd_doc(dni):
        dni_u = dni.upper()
        return dni_u == settings.CITIZEN_ND or dni_u == getattr(settings, 'CITIZEN_NDD', 'NDD')

    @property
    def is_nd(self):
        return self.document == settings.CITIZEN_ND

    @property
    def is_ndd(self):
        return self.document == getattr(settings, 'CITIZEN_NDD', 'NDD')

    @property
    def can_be_anonymized(self):
        if self.social_entity:
            return False
        return not RecordCard.objects.applicants_open_records([self.pk])

    def anonymize(self):
        if not self.citizen:
            return

        if self.can_be_anonymized:
            CitizenAnonymize(self.citizen).anonymize()
            self.pend_anonymize = False
        else:
            self.pend_anonymize = True
        self.save()

    def clean(self):
        super().clean()
        self.check_citizen_social_entity_assignation(self.citizen, self.social_entity)

    def save_applicant_response(self, recordcard_response, authorization=True):
        if not Applicant.is_nd_doc(self.document) and recordcard_response.language != ENGLISH:
            if hasattr(self, "applicantresponse"):
                applicant_response = self.applicantresponse
            else:
                applicant_response = ApplicantResponse()
                applicant_response.applicant = self

            self.update_contact_information(applicant_response, recordcard_response)
            self.update_ubication_information(applicant_response, recordcard_response)
            applicant_response.authorization = authorization
            self.flag_ca = authorization
            self.save()
            applicant_response.save()
            return applicant_response

    @staticmethod
    def update_contact_information(applicant_response, recordcard_response):
        applicant_response.language = recordcard_response.language
        if recordcard_response.response_channel_id == ResponseChannel.EMAIL:
            applicant_response.email = recordcard_response.address_mobile_email
        elif recordcard_response.response_channel_id == ResponseChannel.TELEPHONE:
            applicant_response.phone_number = recordcard_response.address_mobile_email
        elif recordcard_response.response_channel_id == ResponseChannel.SMS:
            applicant_response.mobile_number = recordcard_response.address_mobile_email

        applicant_response.response_channel_id = recordcard_response.response_channel_id

    @staticmethod
    def update_ubication_information(applicant_response, recordcard_response):
        applicant_response.street_type = recordcard_response.via_type
        if recordcard_response.response_channel_id == ResponseChannel.LETTER:
            applicant_response.street = recordcard_response.address_mobile_email
        applicant_response.number = recordcard_response.number
        applicant_response.floor = recordcard_response.floor
        applicant_response.door = recordcard_response.door
        applicant_response.door = recordcard_response.door
        applicant_response.scale = recordcard_response.stair
        applicant_response.postal_code = recordcard_response.postal_code
        applicant_response.municipality = recordcard_response.municipality
        applicant_response.province = recordcard_response.province

    def is_internal_operator(self, applicant_type_id, input_channel_id):
        try:
            InternalOperator.objects.get(applicant_type_id=applicant_type_id, input_channel_id=input_channel_id,
                                         document=self.document)
            return True
        except InternalOperator.DoesNotExist:
            return False


class ApplicantResponse(UserTrack):
    """
    IRS_TB_RESPOSTA_SOLICITANT
    """
    applicant = models.OneToOneField(Applicant, verbose_name=_(u"Applicant"), on_delete=models.PROTECT)
    language = models.CharField(_("Language"), max_length=2, choices=LANGUAGES, default=SPANISH)
    phone_number = models.CharField(_(u"Phone Number"), max_length=30, blank=True, db_index=True)
    mobile_number = models.CharField(_(u"Mobile Number"), max_length=30, unique=False, db_index=True)
    email = models.EmailField(_(u"Email"), max_length=50, unique=False, blank=True, db_index=True)

    street_type = models.CharField(_(u"Street Type"), max_length=60)
    street = models.CharField(_(u"Street"), max_length=300, db_index=True)
    number = models.CharField(_(u"Number"), max_length=60)
    floor = models.CharField(_(u"Floor"), max_length=50, blank=True)
    door = models.CharField(_(u"Door"), max_length=20, blank=True)
    scale = models.CharField(_(u"Scale"), max_length=20, blank=True)
    postal_code = models.CharField(_(u"Postal Code"), max_length=10)
    municipality = models.CharField(_(u"Municipality"), max_length=150)
    province = models.CharField(_(u"Province"), max_length=150)

    response_channel = models.ForeignKey(ResponseChannel, on_delete=models.PROTECT)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    authorization = models.BooleanField(_(u"Authorization"), default=False)

    def __str__(self):
        return "{} {}".format(self.applicant.__str__(), self.response_channel.__str__())


class Request(UserTrack):
    """
    IRS_TB_PETICIO
    """
    applicant = models.ForeignKey(Applicant, null=True, blank=True, verbose_name=_(u"Applicant"),
                                  on_delete=models.PROTECT)
    applicant_type = models.ForeignKey(ApplicantType, verbose_name=_(u"Applicant Type"), on_delete=models.PROTECT)
    application = models.ForeignKey(Application, verbose_name=_(u"Application"), on_delete=models.PROTECT,
                                    null=True, blank=True)
    input_channel = models.ForeignKey(InputChannel, verbose_name=_(u"Input Channel"), on_delete=models.PROTECT)
    communication_media = models.ForeignKey(CommunicationMedia, verbose_name=_(u"Communication Media"),
                                            null=True, on_delete=models.PROTECT)

    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    normalized_id = models.CharField(_(u"Normalized ID"), max_length=60, blank=True)

    def __str__(self):
        return "{} {}".format(self.applicant.__str__(), self.input_channel.__str__())


class RecordCard(UserTrack):
    """
    IRS_TB_FITXA
    """
    ATE_PAGE_ORIGIN = "ATENCIO EN LINIA"

    objects = RecordCardQueryset.as_manager()
    user_id = UserIdField(db_index=True)
    created_at = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)

    description = models.TextField(verbose_name=_("Description"))
    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.PROTECT,
                                       db_index=True)
    original_element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), null=True,
                                                on_delete=models.PROTECT, editable=False, related_name="original_theme",
                                                help_text=_("Field for traceability and report purpose. Not edit"))
    request = models.ForeignKey(Request, verbose_name=_(u"Request"), on_delete=models.PROTECT, null=True, blank=True)
    responsible_profile = models.ForeignKey(Group, verbose_name=_(u"Responsible profile"), null=True, blank=True,
                                            on_delete=models.PROTECT, db_index=True)
    reasigned = models.BooleanField(_("Reasigned"), default=False,
                                    help_text=_("Shows if RecordCard has been manually reasigned or not"))
    ubication = models.ForeignKey(Ubication, verbose_name=_(u"Ubication"), on_delete=models.PROTECT,
                                  null=True, blank=True)
    process = models.ForeignKey(Process, on_delete=models.PROTECT, verbose_name=_(u"Process"), null=True, blank=True)
    record_state = models.ForeignKey(RecordState, verbose_name=_(u"Record State"), on_delete=models.PROTECT,
                                     db_index=True)
    record_type = models.ForeignKey(RecordType, verbose_name=_(u"Record Type"), on_delete=models.PROTECT, db_index=True)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    mayorship = models.BooleanField(_(u"Mayorship"), default=False, db_index=True)
    normalized_record_id = models.CharField(_(u"Normalized Record Id"), max_length=20, blank=True, unique=True)
    alarm = models.BooleanField(_(u"Alarm"), default=False, db_index=True)
    applicant_type = models.ForeignKey(ApplicantType, verbose_name=_(u"Applicant Type"), on_delete=models.PROTECT,
                                       db_index=True)
    auxiliary = models.CharField(_(u"Auxiliary"), max_length=40, blank=True)
    closing_date = models.DateTimeField(_(u"Closing date"), null=True, blank=True, db_index=True)
    ans_limit_date = models.DateTimeField(_(u"ANS limit date"), null=True, blank=True, db_index=True)
    ans_limit_nearexpire = models.DateTimeField(_(u"ANS limit near expire"), null=True, blank=True, db_index=True)
    communication_media = models.ForeignKey(CommunicationMedia, verbose_name=_(u"Communication Media"),
                                            on_delete=models.PROTECT, null=True, blank=True, db_index=True)
    communication_media_date = models.DateField(_(u"Communication Media Date"), null=True, blank=True)
    communication_media_detail = models.CharField(_(u"Communication Media Detail"), max_length=100, blank=True)
    support = models.ForeignKey(Support, on_delete=models.PROTECT, db_index=True)
    record_parent_claimed = models.CharField(_(u"Record Parent Claimed"), max_length=30, blank=True)
    reassignment_not_allowed = models.BooleanField(_(u"Reassignment not Allowed"), default=False)
    urgent = models.BooleanField(_(u"Urgent"), default=False, db_index=True)
    page_origin = models.CharField(_(u"Page origin"), max_length=100, blank=True)
    email_external_derivation = models.EmailField(_(u"Email external derivation"), blank=True)
    user_displayed =UserIdField(verbose_name=_(u"User displayed"), blank=True)
    historicized = models.CharField(_(u"Historicized"), max_length=3, default="N")
    allow_multiderivation = models.BooleanField(_(u"Allow Multiderivation"), default=False)
    start_date_process = models.DateField(_(u"Start Date Process"), null=True, blank=True)
    appointment_time = models.TimeField(_(u"Appointment Time"), null=True, blank=True)
    similar_process = models.BooleanField(_(u"Similar process"), default=False)
    possible_similar = models.ManyToManyField("self", verbose_name=_("Possible Similar Records"))
    possible_similar_records = models.BooleanField(_(u"Possible Similar Records"), default=False)
    response_state = models.CharField(_(u"Response State"), max_length=40, blank=True)
    notify_quality = models.BooleanField(_(u"Notify quality"), null=True, blank=True)
    multi_complaint = models.PositiveIntegerField(_(u"Multi complaint"), null=True, blank=True)
    multirecord_from = models.ForeignKey("self", verbose_name=_("MultiRecord From"), on_delete=models.PROTECT,
                                         null=True, blank=True)
    is_multirecord = models.BooleanField(_(u"Is MultiRecord"), default=False)
    lopd = models.NullBooleanField(_(u"LOPD"), null=True, blank=True)
    input_channel = models.ForeignKey(InputChannel, on_delete=models.PROTECT, db_index=True)
    ci_date = models.DateField(_(u"CI Date"), null=True, blank=True)
    support_numbers = models.PositiveIntegerField(_(u"Support Numbers"), default=0)

    features = models.ManyToManyField(Feature, through="record_cards.RecordCardFeatures", blank=True)
    special_features = models.ManyToManyField(Feature, through="record_cards.RecordCardSpecialFeatures", blank=True,
                                              related_name="special_features")
    workflow = models.ForeignKey("record_cards.Workflow", verbose_name=_(u"Workflow"), on_delete=models.PROTECT,
                                 null=True, blank=True)

    pend_applicant_response = models.BooleanField(_(u"Pend Applicant Response"), default=False)
    applicant_response = models.BooleanField(_(u"Applicant Response"), default=False)
    pend_response_responsible = models.BooleanField(_(u"Pend Response to Record Responsible"), default=False)
    response_to_responsible = models.BooleanField(_(u"Response to Record Responsible"), default=False)
    response_time_expired = models.BooleanField(_(u"Response Time Expired"), default=False)

    claimed_from = models.ForeignKey("self", verbose_name=_("Claim From"), on_delete=models.PROTECT,
                                     null=True, blank=True, related_name="claim")
    claims_number = models.PositiveIntegerField(_(u"Number of claims"), default=0)
    citizen_alarm = models.BooleanField(_(u"Citizen alarm"), default=False, db_index=True)
    citizen_web_alarm = models.BooleanField(_(u"Citizen web alarm"), default=False, db_index=True)
    cancel_request = models.BooleanField(_("Cancel Request"), default=False)

    # department info
    creation_department = models.CharField(_("Department on creation"), max_length=200, blank=True, db_index=True)
    close_department = models.CharField(_("Department on cancelation"), max_length=200, blank=True)
    creation_group = models.ForeignKey(Group, verbose_name=_(u"Creation group"), null=True, blank=True,
                                       on_delete=models.PROTECT, related_name="create_records")
    organization = models.CharField(_("Organization"), max_length=100, blank=True)

    def __str__(self):
        return self.description[:100]

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.pk:
            self.reassignment_not_allowed = False
            self.original_element_detail = self.element_detail
            self._set_ans_limits()
            initial_state = RecordState.PENDING_VALIDATE
            if self.element_detail.requires_citizen and not self.request.applicant:
                initial_state = RecordState.NO_PROCESSED
            self.record_state_id = initial_state
            self.set_detail()
            if not self.normalized_record_id:
                self.normalized_record_id = set_reference(RecordCard, "normalized_record_id")

        if not self.request_id:
            citizen, _ = Citizen.objects.get_or_create(name="Ajuntament", first_surname="Barcelona", birth_year=1900,
                                                       district_id=District.CIUTAT_VELLA)
            applicant, _ = Applicant.objects.get_or_create(citizen=citizen)
            request, _ = Request.objects.get_or_create(applicant=applicant, applicant_type_id=ApplicantType.CIUTADA,
                                                       input_channel=self.input_channel,
                                                       communication_media=self.communication_media,
                                                       normalized_id=set_reference(Request, "normalized_id"))
            self.request = request

        super().save(force_insert, force_update, using, update_fields)

    def _set_ans_limits(self, from_time=None):
        if not from_time:
            from_time = timezone.now()

        delta_hours = self.element_detail.ans_delta_hours
        self.ans_limit_date = from_time + timedelta(hours=delta_hours)

        percentage_expire = 1 - int(Parameter.get_parameter_by_key("PERCENTATGE_PROPERA_EXPIRACIO", 10)) / 100
        delta_nearexpire = round(delta_hours * percentage_expire)
        self.ans_limit_nearexpire = from_time + timedelta(hours=delta_nearexpire)

    def update_ans_limits(self, do_save=True):
        self._set_ans_limits(from_time=self.created_at)
        if do_save:
            self.save()

    def show_late_answer_text(self):
        days_for_text = int(Parameter.get_parameter_by_key('DIES_DISCULPES_RETARD', 30))
        return self.created_at + timedelta(days=days_for_text) < timezone.now()

    @property
    def language(self):
        lang = get_default_lang()
        if hasattr(self, 'recordcardresponse') and self.recordcardresponse.language:
            lang = self.recordcardresponse.language
        elif self.request.applicant.language:
            lang = self.request.applicant.language
        return lang

    def send_record_card_created(self):
        record_card_created.send_robust(sender=RecordCard, record_card=self)

    def send_record_card_state_changed(self):
        from record_cards.tasks import anonymize_applicant
        if self.record_state_id in RecordState.DEF_CLOSED_STATES and self.request.applicant \
          and self.request.applicant.pend_anonymize:
            anonymize_applicant.delay(self.request.applicant_id)
        record_card_state_changed.send_robust(sender=RecordCard, record_card=self)

    def set_detail(self, set_proces=True):
        self.record_type = self.element_detail.record_type
        if set_proces:
            self.process = self.element_detail.process

    def update_detail_info(self):
        set_process = True if self.record_state_id in RecordState.PEND_VALIDATE_STATES else False
        self.set_detail(set_process)
        self.save()

    @property
    def ideal_path(self):
        return RecordCardStateMachine(self).get_ideal_path()

    @property
    def current_step(self):
        return RecordCardStateMachine(self).get_current_step()

    @property
    def next_step_code(self):
        return RecordCardStateMachine(self).get_next_step_code()

    def get_state_change_method(self, next_state_id):
        return RecordCardStateMachine(self).get_state_change_method(next_state_id)

    @property
    def is_validated(self):
        return self.record_state_id not in RecordState.PEND_VALIDATE_STATES

    @property
    def validate_date_limit(self):
        return self.created_at + timedelta(days=self.element_detail.validation_place_days)

    @property
    def can_be_validated(self):
        if not self.element_detail.validation_place_days:
            return True
        return timezone.now() < self.validate_date_limit

    def has_expired(self, group):
        """
        :param group: group to check the max reasign days outside ambit
        :return: True if it is not validated and has overcome the period of reassign else False
        """
        if RECARD_COORDINATOR_VALIDATION_DAYS in group.group_permissions_codes:
            max_reasign_days_outsite_ambit = int(Parameter.get_parameter_by_key("TERMINI_VALIDACIO_COORD", 10))
        else:
            max_reasign_days_outsite_ambit = int(Parameter.get_parameter_by_key("DIES_REASSIGNACIO_FORA_AMBIT", 5))
        return not self.is_validated and self.days_in_ambit >= max_reasign_days_outsite_ambit

    def group_can_tramit_record(self, user_group) -> bool:
        """
        A group can tramit record card if it's the responsible or it's an ascendant of its responsible profile

        :param user_group: Group to check
        :return: True if user can tramit the RecordCard, else False
        """
        return user_group.group_plate in self.responsible_profile.group_plate

    def group_can_open_conversation(self, user_group, user=None) -> bool:
        """
        A group can open a conversation on the recordCard if it can tramit the record

        :param user_group: Group to check
        :param user: user to check
        :return: True if user can open conversations on the RecordCard, else False
        """
        return self.group_can_tramit_record(user_group)

    def only_answer_ambit_coordinators(self):
        """
        Check if only record card can be answered by an ambit coordinator
        - If RecordCard has been claimend more than 5 times
        - If RecordCard is more than DIES_ANTIGUITAT_RESPOSTA (90 by default) days old
        :return: True if record cand can only be answered by an ambit coordinator else False
        """

        if self.claims_number >= int(Parameter.get_parameter_by_key("FITXES_PARE_RESPOSTA", 5)):
            return {"only_coordinators": True, "reason": _("The number of claims is greater or equal than "
                                                           "the configured limit")}

        old_response_days = int(Parameter.get_parameter_by_key("DIES_ANTIGUITAT_RESPOSTA", 90))

        if self.created_at < timezone.now() - timedelta(days=old_response_days):
            return {"only_coordinators": True, "reason": _("The record has overcome the limit of days to response")}
        return {"only_coordinators": False}

    def group_can_answer(self, user_group):
        """
        Define if a group can answer the record or not.
        - If record is not only for group ambit manage, group can answer it
        - Else:
        -  if user group is an ambit, group can answer it
        -  else, grop can NOT answer it

        :param user_group:
        :return: True if a group can answer the record else False
        """
        if not user_group:
            return {"can_answer": False, "reason": _("User's group not detected")}

        if Group.get_dair_group() == user_group:
            return {"can_answer": True}
        only_is_ambit = self.only_answer_ambit_coordinators()
        if not only_is_ambit["only_coordinators"] or user_group.is_ambit:
            return {"can_answer": True}
        else:
            return {"can_answer": False, "reason": only_is_ambit["reason"]}

    def change_state(self, next_state_code, user, user_department, group=None, automatic=False,
                     perform_derivation=True):
        """
        Updated record state, derivate the record and register the state change

        :param next_state_code: new state code
        :param user: user of the request
        :param user_department: department of user
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :param perform_derivation: if True, derivation is done, else not
        :return:
        """
        previous_state_code = self.record_state_id
        self.record_state_id = next_state_code

        if next_state_code in RecordState.DEF_CLOSED_STATES:
            self.set_close_data(user_department, user)
        self.save()
        if perform_derivation:
            self.derivate(get_user_traceability_id(user), next_state_id=next_state_code)
        self.set_record_state_history(next_state_code, user, previous_state_code=previous_state_code, group=group,
                                      automatic=automatic)

    def pending_answer_change_state(self, next_state_code, user, user_department, group=None, automatic=False,
                                    perform_derivation=True) -> int:
        """
        Check

        :param next_state_code: new state code
        :param user: user of the request
        :param user_department: department of user
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :param perform_derivation: if True, derivation is done, else not
        :return: Finally state code set
        """
        if not group:
            group = user.usergroup.group if user and hasattr(user, "usergroup") else None

        if not hasattr(self, "recordcardresponse") or \
            self.recordcardresponse.get_response_channel() == ResponseChannel.NONE:
            final_state_code = RecordState.CLOSED
            self.change_state(final_state_code, user, user_department, group=group, automatic=True,
                              perform_derivation=perform_derivation)
            comment = _("Automatically closed record because response has not to be sent")
            Comment.objects.create(record_card=self, group=group, reason_id=Reason.RECORDCARD_AUTOMATICALLY_CLOSED,
                                   comment=comment)
        else:
            self.change_state(next_state_code, user, user_department, group=group, automatic=automatic,
                              perform_derivation=perform_derivation)
            final_state_code = next_state_code
        return final_state_code

    def pending_answer_has_toclose_automatically(self, response_channel_id):
        return self.record_state_id == RecordState.PENDING_ANSWER and response_channel_id == ResponseChannel.NONE

    def set_record_state_history(self, next_state_code, user, previous_state_code=None, group=None, automatic=False):
        """
        Set the recordStateHistory register for a state change on a RecordCard

        :param next_state_code: new state code
        :param user: user of the request
        :param previous_state_code: optional previous state code
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :return:
        """
        if not group:
            group = user.usergroup.group if hasattr(user, "usergroup") else None
        previous_state_id = previous_state_code if previous_state_code is not None else self.record_state_id
        user_name = get_user_traceability_id(user)
        RecordCardStateHistory.objects.create(record_card=self, group=group, previous_state_id=previous_state_id,
                                              next_state_id=next_state_code, user_id=user_name, automatic=automatic)

    def record_can_be_autovalidated(self, new_element_detail=None):
        """
        A record card can be autovalidated if:
        - it is in a pending state
        - element detail has the flag autovalidate_records set to true
        - it has applicant

        :param new_element_detail: Possible new element detail
        :return: True if record card can be autovalidated, else False
        """

        if self.record_state_id not in RecordState.PEND_VALIDATE_STATES:
            return False

        element_detail = new_element_detail if new_element_detail else self.element_detail
        if not element_detail.autovalidate_records:
            return False

        if not self.request.applicant:
            return False

        return True

    @property
    def external_is_mandatory(self):
        """
        If it has external_service_id and is not external managed, we have to ask user if he wants to send the record
        or manage it on iris
        :return: True if external service is mandatory
        """
        return 'external_service_id' in Process.REQUIRED.get(self.process_id, [])

    def has_to_external_validate(self, external_validator, send_external=False):
        return external_validator and (self.external_is_mandatory or send_external)

    def autovalidate_record(self, user_department, user, perform_derivation=True):
        external_validator = get_external_validator(self)
        if external_validator:
            if not getattr(external_validator, "support_autovalidation", False):
                return

            if not external_validator.validate():
                # Add comment
                Comment.objects.create(record_card_id=self.pk, reason_id=Reason.OBSERVATION,
                                       comment="S'ha produït un error en enviar la fitxa al serveï extern. "
                                               "S'haurà de tornar a fer manualment")
                return

        validation_kwargs = {
            "user_department": user_department,
            "user": user,
            "next_state_code": self.next_step_code,
            "automatic": True,
            "perform_derivation": perform_derivation
        }

        if not external_validator or not external_validator.handle_state_change(**validation_kwargs):
            self.validate(**validation_kwargs)

    def validate(self, user_department, user, next_state_code=None, similar_record=None, automatic=False,
                 perform_derivation=True):
        """
        Validate the RecordCard and associate it to its workflow. If thers is a similar_record, get the data from it
        Process the state change
         :param user_department: department of user
         :param user: user of the request
         :param next_state_code: if it"s set, it"s the new state code else it has to be calculated
         :param similar_record: if it"s set, it"s the RecordCard to validate the current with
         :param automatic: set to True if the state change has been done automatically
         :param perform_derivation: if True, derivation is done during state change, else not
        :return:
        """
        if similar_record:
            self.workflow = similar_record.workflow
            next_state = similar_record.record_state_id
            self.similar_process = True
            self.alarm = True
            similar_record.similar_process = True
            similar_record.alarm = True
            similar_record.save()
        else:
            if not next_state_code:
                next_state_code = self.next_step_code
            self.workflow = Workflow.objects.create(main_record_card=self, state_id=next_state_code)
            next_state = next_state_code
        if next_state == RecordState.EXTERNAL_PROCESSING and not self.closing_date:
            self.closing_date = timezone.now()

        self.register_audit_field("validation_user", get_user_traceability_id(user))

        state_change = getattr(self, self.get_state_change_method(next_state))
        state_change(next_state, user, user_department, automatic=automatic, perform_derivation=perform_derivation)

    def will_be_tramited(self, applicant, user_department, user):
        self.request.applicant = applicant
        self.request.save()
        state_change = getattr(self, self.get_state_change_method(RecordState.PENDING_VALIDATE))
        state_change(RecordState.PENDING_VALIDATE, user, user_department, automatic=False, perform_derivation=True)

    def set_close_data(self, close_department, user, perform_save=False):
        """
        Register information of closing record card

        :param close_department: department of the user that closes the record
        :param user: user of the request
        :param perform_save: bool to indicate if record has to be saved
        :return:
        """
        self.closing_date = timezone.now()
        self.close_department = close_department
        self.register_audit_field("close_user", get_user_traceability_id(user))
        if perform_save:
            self.save(update_fields=["closing_date", "close_department", "updated_at"])

    @property
    def cant_set_applicant(self):
        limit_days = int(Parameter.get_parameter_by_key("DIES_AFEGIR_CIUTADA", 30))
        return (timezone.now() - self.created_at).days > limit_days

    def derivate(self, user_id, next_state_id=None, next_district_id=None, is_check=False, new_element_detail_id=None,
                 reason=None):
        """
        If a derivation for the RecordCard and the next state exist, change the responsible profile of RecordCard
        If RecordCard has been reassigned and is not allow to derivate, it can not be derivated
        :param user_id: User that is performing the operation
        :param next_state_id: Next state id for record card. If none, use current record_card state
        :param next_district_id: Next district id for record card. If none, use current district
        :param is_check: if False, do actions on derivations
        :param new_element_detail_id: element detail on change
        :param reason:

        :return: group to derivate or none
        """
        if new_element_detail_id:
            try:
                self.element_detail = ElementDetail.objects.get(pk=new_element_detail_id)
            except ElementDetail.DoesNotExist:
                pass

        if self.record_state_id not in RecordState.PEND_VALIDATE_STATES and \
                self.reasigned and not self.allow_multiderivation:
            return

        if not next_state_id:
            next_state_id = self.record_state_id
        if not next_district_id and self.ubication_id:
            next_district_id = self.ubication.district_id

        try:
            derivation_group = derivate(self, next_state_id, next_district_id, is_check=is_check)
            if reason == Reason.INITIAL_ASSIGNATION and not derivation_group:
                derivation_group = derivate(self, RecordState.PENDING_VALIDATE, next_district_id, is_check=is_check)
        except Exception:
            logger.exception('Error when finding derivation')
            derivation_group = Group.get_default_error_derivation_group()
        # If the use of the method is a check, we return the derivation group here and don"t do any action more
        if is_check:
            return derivation_group
        self._perform_derivation(derivation_group, reason, user_id)
        return derivation_group

    def _perform_derivation(self, derivation_group, reason, user_id):
        if derivation_group and derivation_group != self.responsible_profile:
            RecordCardReasignation.objects.create(user_id=user_id, record_card=self, group=self.responsible_profile,
                                                  previous_responsible_profile=self.responsible_profile,
                                                  next_responsible_profile=derivation_group,
                                                  reason_id=reason if reason else Reason.DERIVATE_RESIGNATION,
                                                  comment=_("Automatic reasignation by derivation"))
            self.responsible_profile = derivation_group
            self.user_displayed = ""
            self.save(update_fields=["responsible_profile", "user_displayed"])
            if reason != Reason.INITIAL_ASSIGNATION:
                send_allocated_notification.delay(derivation_group.pk, self.pk)

            # When the responsible profile change, all RecordCardConversations has to be closed
            self.close_record_conversations()

    @property
    def active_blocks(self):
        now = timezone.now()
        return self.recordcardblock_set.filter(expire_time__gte=now)

    @property
    def current_block(self):
        return self.active_blocks.first()

    def is_blocked(self, request_username):
        """
        Check if record card is blocked by other users

        :param request_username: Username to check if RecordCard is blocked or not
        :return: True if RecordCard is blocked, else False
        """
        user_active_blocks = self.active_blocks.exclude(user_id=request_username)
        if not user_active_blocks:
            return False
        return True

    def set_internal_claim(self):
        self.input_channel_id = InputChannel.RECLAMACIO_INTERNA  # Internal Claim InputChannel pk
        self.applicant_type_id = ApplicantType.RECLAMACIO_INTERNA  # Internal Claim ApplicantType pk
        self.support_id = Support.RECLAMACIO_INTERNA  # Internal Claim Support pk

    def exceed_temporary_proximity(self, possible_similar):
        """
        :param possible_similar: RecordCard to compare temporary proximity
        :return: True if the time difference between RecordCards exceed temporary proximity
        """
        if self.created_at > possible_similar.created_at:
            time_difference = self.created_at - possible_similar.created_at
        else:
            time_difference = possible_similar.created_at - self.created_at
        time_difference_seconds = time_difference.days * 24 * 3600 + time_difference.seconds
        similarity_seconds = self.element_detail.similarity_hours * 3600
        return True if time_difference_seconds > similarity_seconds else False

    def exceed_meters_proximity(self, possible_similar):
        """
        :param possible_similar: RecordCard to compare temporary proximity
        :return: True if the meters difference between RecordCards exceed meters proximity or one of the
        record has no ubication
        """
        if not self.ubication or not possible_similar.ubication:
            return True

        distance_ubications = self.ubication.distance(possible_similar.ubication)

        # If distance between ubications is not kwnown, meters proximity is considered exceeded
        if distance_ubications is None:
            return True

        # If distance between ubications is greater than the similarity meters, meters proximity is considered exceeded
        if distance_ubications > self.element_detail.similarity_meters:
            return True

        return False

    def get_possible_similar_records(self):
        """
        Get the possible similar records without taking in acount if they are previously validated.
        This method is used during record card creation and update. Then, the list of possible similar that we offer
        on the view is filtered by the validated Records
        :return: A list of possible similar RecordCards
        """
        possible_similar_records = []

        records = RecordCard.objects.filter(responsible_profile__isnull=False,
                                            element_detail_id=self.element_detail_id,
                                            record_state_id__in=RecordState.OPEN_STATES).exclude(pk=self.pk)
        if self.element_detail.similarity_hours:
            from_date = self.created_at - timedelta(hours=self.element_detail.similarity_hours)
            to_date = self.created_at + timedelta(hours=self.element_detail.similarity_hours)
            records = records.filter(created_at__gte=from_date, created_at__lte=to_date)

        for possible_similar in records:
            if self.element_detail.similarity_meters and self.exceed_meters_proximity(possible_similar):
                continue
            possible_similar_records.append(possible_similar)
        return possible_similar_records

    def check_similarity(self, possible_similar, user):
        """
        Compare the current RecordCard and another to check if they are similar. Follow the criterion commented,
        taking in account that the possible similar RecordCard must be previously validated. This method is used during
        similar RecordCard validation to be sure that current record can be validated this way.

        :param possible_similar: RecordCard to compare similarity with  the actual one
        :param user: User that is checking the similarity
        :return: True if actual RecordCard and possible_similar_record are similar
        """
        # First similarity criterion: Possible similar record has to be validated and not in a closed state
        similar_state = possible_similar.record_state_id
        if similar_state in RecordState.PEND_VALIDATE_STATES or similar_state in RecordState.CLOSED_STATES:
            return False

        # Second similarity criterion: both RecordCards has the same theme
        if self.element_detail_id != possible_similar.element_detail_id:
            return False
        # If user has no permission to validate a record through a worflow outsite record's ambit,
        # the third similarity criterion is applied
        if not IrisPermissionChecker.get_for_user(user).has_permission(RECARD_VALIDATE_OUTAMBIT):
            # Thrid similarity criterion: the responsible profiles has to be at the same ambit
            if self.responsible_profile.get_ambit_parent() != possible_similar.responsible_profile.get_ambit_parent():
                return False

        # Fourth similarity criterion: the difference between the created_at of the records can not exceed
        # the limit of temporary proximity established by the theme
        if self.element_detail.similarity_hours:
            if self.exceed_temporary_proximity(possible_similar):
                return False

        # Fifth similarity criterion: the difference between the ubications of the records can not exceed
        # the limit of the meters proximity established by the theme
        if self.element_detail.similarity_meters:
            if self.exceed_meters_proximity(possible_similar):
                return False

        return True

    def set_similar_records(self):
        """
        Register similar records from current record card
        :return:
        """
        with transaction.atomic():
            # Set possible similar records alarm to False by default and clear possible similar relations
            self.possible_similar_records = False
            if not RecordCardAlarms(self, self.responsible_profile).check_alarms(["possible_similar_records"]):
                alarm = False
            else:
                alarm = True
            RecordCard.objects.filter(pk=self.pk).update(possible_similar_records=False, alarm=alarm)
            self.possible_similar.clear()

            possible_similar_records = self.get_possible_similar_records()
            if possible_similar_records:
                records_similar_pks = []
                for possible_similar in possible_similar_records:
                    if self.record_state_id in RecordState.PEND_VALIDATE_STATES \
                        and possible_similar.record_state_id not in RecordState.PEND_VALIDATE_STATES:
                        # Set possible similar records alarm to True if the there's a possible similar validated
                        records_similar_pks.append(possible_similar.pk)
                    self.possible_similar.add(possible_similar)
                if records_similar_pks:
                    records_similar_pks.append(self.pk)
                    RecordCard.objects.filter(pk__in=records_similar_pks).update(possible_similar_records=True,
                                                                                 alarm=True)

    def create_record_claim(self, user_id, claim_description, is_web_claim=False, set_to_internal_claim=False,
                            set_alarms=True, creation_department=None):
        """
        Create claim and update the number of claims registered.
        :param user_id: user_id which is creating the claim
        :param claim_description: new description for claim
        :param is_web_claim: indicates if it"s a web claim or not
        :param set_to_internal_claim: indicates if it"s a an internal claim
        :param set_alarms: indicates if alarms has to be set or not
        :param creation_department: department of creation
        :return: Claim (RecordCard) object
        """

        # create claim
        claim = deepcopy(self)
        claim.pk = None
        claim.multirecord_from = None
        claim.multi_complaint = None
        claim.is_multirecord = False
        claim.workflow = None
        claim.similar_process = False
        claim.possible_similar_records = False
        claim.closing_date = None
        claim.reasigned = False
        claim.pend_applicant_response = False
        claim.applicant_response = False
        claim.pend_response_responsible = False
        claim.response_to_responsible = False
        claim.response_time_expired = False
        claim.citizen_alarm = False
        claim.citizen_web_alarm = False
        claim.cancel_request = False
        claim.alarm = False

        # update claim data
        if user_id:
            claim.user_id = user_id
        claim.description = claim_description
        # change state to pend to validate
        claim.record_state_id = RecordState.PENDING_VALIDATE
        # calculate new normalized_record_id
        claim.normalized_record_id, claim.claims_number = generate_next_reference(self.normalized_record_id)
        claim.claimed_from_id = self.pk
        if is_web_claim:
            claim.page_origin = RecordCard.ATE_PAGE_ORIGIN
        if creation_department:
            claim.creation_department = creation_department
        if set_to_internal_claim:
            claim.set_internal_claim()

        claim.update_ans_limits(do_save=False)

        if set_alarms:
            claim.citizen_alarm = True
            claim.alarm = True

            if is_web_claim:
                self.citizen_web_alarm = True
                claim.citizen_web_alarm = True

            self.citizen_alarm = True
            self.alarm = True

        claim.save()
        self.claims_number = claim.claims_number
        self.save(update_fields=["citizen_web_alarm", "citizen_alarm", "alarm", "claims_number"])

        if getattr(self, "recordcardresponse", None):
            rc_resp = deepcopy(self.recordcardresponse)
            rc_resp.pk = None
            rc_resp.record_card = claim
            rc_resp.save()

        for record_card_feature in self.recordcardfeatures_set.all():
            record_card_feature.pk = None
            record_card_feature.record_card = claim
            record_card_feature.save()

        for record_card_feature in self.recordcardspecialfeatures_set.all():
            record_card_feature.pk = None
            record_card_feature.record_card = claim
            record_card_feature.save()

        if not set_to_internal_claim:
            claim.derivate(user_id=user_id, reason=Reason.INITIAL_ASSIGNATION)
        claim.send_record_card_created()

        return claim

    def copy_files(self, user_group, copy_files_from_record_pk):
        from record_cards.tasks import copy_record_files
        Comment.objects.create(group=user_group, reason_id=Reason.COPY_FILES,
                               record_card=self, comment=_("Copying files"))
        copy_record_files.delay(copy_files_from_record_pk, self.pk, user_group.pk)

    def update_claims_number(self):
        """
        Update the number of claims on all Record related to claim
        :return:
        """
        base_normalized_record_id = self.normalized_record_id.split("-")[0]
        RecordCard.objects.filter(
            normalized_record_id__startswith=base_normalized_record_id
        ).update(
            claims_number=self.claims_number
        )

    @property
    def is_claimed(self):
        if not self.claims_number:
            return False
        return False if self.claim_num in self.normalized_record_id else True

    @property
    def claim_num(self):
        return "-0{}".format(self.claims_number) if self.claims_number < 10 else "-{}".format(self.claims_number)

    def get_last_claim_code(self):
        normalized_record_id = self.normalized_record_id.split("-")[0]
        return "{}{}".format(normalized_record_id, self.claim_num)

    def get_last_claim(self):
        if not self.is_claimed:
            return None
        return RecordCard.objects.get(normalized_record_id=self.get_last_claim_code())

    def get_record_audit(self):
        if hasattr(self, "recordcardaudit"):
            return self.recordcardaudit
        return RecordCardAudit.objects.create(record_card=self)

    def register_audit_field(self, audit_field, audit_value):
        record_audit = self.get_record_audit()
        setattr(record_audit, audit_field, audit_value)
        record_audit.save(update_fields=[audit_field])

    def close_record_conversations(self, update_alarms=True):
        """
        Close record internal conversations and turn off alarms related, recalculating for external converstions
        :return:
        """
        from communications.models import Conversation
        from record_cards.record_actions.conversations_alarms import RecordCardConversationAlarms
        self.conversation_set.filter(type=Conversation.INTERNAL).close_conversations()

        conversation_alarms = RecordCardConversationAlarms(self, [Conversation.EXTERNAL])
        self.response_to_responsible = conversation_alarms.response_to_responsible
        self.pend_response_responsible = conversation_alarms.pend_response_responsible
        self.save(update_fields=["response_to_responsible", "pend_response_responsible"])

    @property
    def days_in_ambit(self):
        ambit_group = self.responsible_profile.get_ambit_coordinator()
        last_ambit_reasignation = self.recordcardreasignation_set.filter(
            ~Q(previous_responsible_profile__group_plate__startswith=ambit_group.group_plate),
            next_responsible_profile__group_plate__startswith=ambit_group.group_plate
        ).order_by("created_at").last()
        if last_ambit_reasignation:
            return (timezone.now() - last_ambit_reasignation.created_at).days
        return (timezone.now() - self.created_at).days


class RecordCardAudit(models.Model):
    """
    IRS_TB_USUARI_FITXA
    """
    record_card = models.OneToOneField(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.PROTECT,
                                       db_index=True)
    validation_user = UserIdField(verbose_name=_("Validation User"), blank=True, db_index=True)
    planif_user = UserIdField(verbose_name=_("Planification User"), blank=True, db_index=True)
    resol_user = UserIdField(verbose_name=_("Resolution User"), blank=True, db_index=True)
    resol_comment = models.TextField(_("Resolution Comment"), blank=True)
    close_user = UserIdField(verbose_name=_("Closing User"), blank=True, db_index=True)

    def __str__(self):
        return "Record {} Audit".format(self.record_card.normalized_record_id)


class RecordCardBlock(UserTrack):
    record_card = models.ForeignKey(RecordCard, verbose_name=_("RecordCard"), on_delete=models.PROTECT)
    expire_time = models.DateTimeField(verbose_name=_("Block expire time"))

    def __str__(self):
        return "RecordCard {} blocked by {} until {}".format(self.record_card_id, self.user_id,
                                                             self.expire_time.strftime("%H:%M  %d/%m/%Y"))

    class Meta:
        indexes = [models.Index(fields=["-expire_time"])]
        ordering = ("-expire_time",)


class RecordCardStateHistory(UserTrack):
    user_id = UserIdField(db_index=True)
    record_card = models.ForeignKey(RecordCard, verbose_name=_("RecordCard"), on_delete=models.PROTECT)
    group = models.ForeignKey(Group, verbose_name=_("Group"), null=True, blank=True, on_delete=models.PROTECT)
    previous_state = models.ForeignKey(RecordState, verbose_name=_("RecordCard Previous State"), db_index=True,
                                       on_delete=models.PROTECT, related_name="previous")
    next_state = models.ForeignKey(RecordState, verbose_name=_("RecordCard Next State"), on_delete=models.PROTECT,
                                   related_name="next", db_index=True)
    automatic = models.BooleanField(_("Automatic"), default=False,
                                    help_text=_("Set to true if the state change has been done automatically"))

    @property
    def record_card_created_at(self):
        return self.record_card.created_at

    def __str__(self):
        return "{} - {}-{}".format(self.record_card.description[:50], self.previous_state.description,
                                   self.next_state.description)


class RecordCardFeatures(CleanEnabledBase, UserTrack):
    """
    IRS_TB_CARACTERISTICA_FITXA
    """
    field_error_name = "feature"

    feature = models.ForeignKey(Feature, verbose_name=_("Feature"), on_delete=models.CASCADE)
    record_card = models.ForeignKey(RecordCard, verbose_name=_("RecordCard"), on_delete=models.CASCADE)
    value = models.CharField(_(u"Value"), max_length=200, blank=True)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    is_theme_feature = models.BooleanField(_(u"Is theme feature"), default=True, db_index=True,
                                           help_text=_("Shows if the related feature is from the current record theme"))

    def __str__(self):
        return "{} - {}".format(self.record_card.description, self.feature.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"record_card": self.record_card, "feature": self.feature}

    class Meta:
        db_table = 'record_cards_recordcardfeaturesaux'


class RecordCardSpecialFeatures(CleanEnabledBase, UserTrack):
    """
    IRS_TB_CARATESP_FITXA
    """
    field_error_name = "feature"

    feature = models.ForeignKey(Feature, verbose_name=_("Feature"), on_delete=models.CASCADE)
    record_card = models.ForeignKey(RecordCard, verbose_name=_("RecordCard"), on_delete=models.CASCADE)
    value = models.CharField(_(u"Value"), max_length=200, blank=True)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    is_theme_feature = models.BooleanField(_(u"Is theme feature"), default=True, db_index=True,
                                           help_text=_("Shows if the related feature is from the current record theme"))

    def __str__(self):
        return "{} - {}".format(self.record_card.description[:100], self.feature.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"record_card": self.record_card, "feature": self.feature}

    @property
    def label_value(self):
        if self.feature.values_type:
            try:
                return self.feature.values_type.values_set.get(id=self.value).description
            except ValueError:
                return self.value
            except Values.DoesNotExist:
                return ""
        return self.value

    class Meta:
        db_table = 'record_cards_recordcardspecialfeaturesaux'


class RecordCardHistory(UserTrack):
    record_card = models.ForeignKey(RecordCard, on_delete=models.CASCADE, verbose_name=_(u"Record Card"))
    description = models.TextField(verbose_name=_("Description"))
    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.PROTECT)
    request = models.ForeignKey(Request, verbose_name=_(u"Request"), on_delete=models.PROTECT, null=True, blank=True)
    responsible_profile = models.ForeignKey(Group, verbose_name=_(u"Responsible profile"), null=True, blank=True,
                                            on_delete=models.PROTECT)
    ubication = models.ForeignKey(Ubication, verbose_name=_(u"Ubication"), on_delete=models.PROTECT,
                                  null=True, blank=True)
    process = models.ForeignKey(Process, on_delete=models.PROTECT, verbose_name=_(u"Process"), null=True, blank=True)
    record_state = models.ForeignKey(RecordState, verbose_name=_(u"Record State"), on_delete=models.PROTECT)
    record_type = models.ForeignKey(RecordType, verbose_name=_(u"Record Type"), on_delete=models.PROTECT)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    mayorship = models.BooleanField(_(u"Mayorship"), default=False)
    normalized_record_id = models.CharField(_(u"Normalized Record Id"), max_length=20, blank=True)
    alarm = models.BooleanField(_(u"Alarm"), default=False)
    applicant_type = models.ForeignKey(ApplicantType, verbose_name=_(u"Applicant Type"), on_delete=models.PROTECT)
    auxiliary = models.CharField(_(u"Auxiliary"), max_length=40, blank=True)
    closing_date = models.DateField(_(u"Closing date"), null=True, blank=True)
    ans_limit_date = models.DateTimeField(_(u"ANS limit date"), null=True, blank=True)
    communication_media = models.ForeignKey(CommunicationMedia, verbose_name=_(u"Communication Media"),
                                            on_delete=models.PROTECT, null=True, blank=True)
    communication_media_date = models.DateField(_(u"Communication Media Date"), null=True, blank=True)
    communication_media_detail = models.CharField(_(u"Communication Media Detail"), max_length=100, blank=True)
    support = models.ForeignKey(Support, on_delete=models.PROTECT)
    record_parent_claimed = models.CharField(_(u"Record Parent Claimed"), max_length=30, blank=True)
    reassignment_not_allowed = models.BooleanField(_(u"Reassignment not Allowed"), default=False)
    urgent = models.BooleanField(_(u"Urgent"), default=False)
    page_origin = models.CharField(_(u"Page origin"), max_length=100, blank=True)
    email_external_derivation = models.EmailField(_(u"Email external derivation"), blank=True)
    user_displayed = UserIdField(verbose_name=_(u"User displayed"))
    historicized = models.CharField(_(u"Historicized"), max_length=3, default="N")
    allow_multiderivation = models.BooleanField(_(u"Allow Multiderivation"), default=True)
    start_date_process = models.DateField(_(u"Start Date Process"), null=True, blank=True)
    appointment_time = models.TimeField(_(u"Appointment Time"), null=True, blank=True)
    similar_process = models.BooleanField(_(u"Similar process"), default=False)
    response_state = models.CharField(_(u"Response State"), max_length=40, blank=True)
    notify_quality = models.PositiveIntegerField(_(u"Notify quality"), null=True, blank=True)
    multi_complaint = models.PositiveIntegerField(_(u"Multi complaint"), null=True, blank=True)
    lopd = models.NullBooleanField(_(u"LOPD"), null=True, blank=True)
    workflow = models.ForeignKey("record_cards.Workflow", verbose_name=_(u"Workflow"), on_delete=models.PROTECT,
                                 null=True, blank=True)
    creation_group = models.ForeignKey(Group, verbose_name=_(u"Creation group"), null=True, blank=True,
                                       on_delete=models.PROTECT, related_name="history_create_records")

    def __str__(self):
        return self.description[:100]


class Comment(UserTrack):
    """
    IRS_TB_COMENTARI
    """
    created_at = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    group = models.ForeignKey(Group, verbose_name=_("Group"), null=True, blank=True, on_delete=models.PROTECT)
    reason = models.ForeignKey(Reason, verbose_name=_("Reason"), null=True, blank=True, on_delete=models.PROTECT)
    record_card = models.ForeignKey(RecordCard, verbose_name=_("Record Card"), on_delete=models.PROTECT, db_index=True,
                                    related_name="comments")
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    comment = models.TextField(_("Comment"))

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return self.comment[:50]


class RecordCardResponse(UserTrack):
    """
    IRS_TB_RESPOSTA_FITXA
    """
    response_channel = models.ForeignKey(ResponseChannel, verbose_name=_(u"Response Channel"), on_delete=models.PROTECT,
                                         db_index=True)
    record_card = models.OneToOneField(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.PROTECT,
                                       db_index=True)
    language = models.CharField(_("Language"), max_length=2, choices=LANGUAGES, default=SPANISH)
    address_mobile_email = models.CharField(_(u"Address, Mobile or Email"), max_length=200, blank=True, db_index=True)
    number = models.CharField(_(u"Number"), max_length=20, blank=True)
    municipality = models.CharField(_(u"Municipality"), max_length=80, blank=True)
    province = models.CharField(_(u"Province"), max_length=80, blank=True)
    postal_code = models.CharField(_(u"Postal code"), max_length=10, blank=True)
    answered = models.BooleanField(_(u"Answered"), default=False)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    via_type = models.CharField(_(u"Via Type"), max_length=35, blank=True)
    via_name = models.CharField(_(u"Via Name"), max_length=100, blank=True)
    floor = models.CharField(_(u"Floor"), max_length=50, blank=True)
    door = models.CharField(_(u"Door"), max_length=20, blank=True)
    stair = models.CharField(_(u"Stair"), max_length=20, blank=True)
    correct_response_data = models.BooleanField(_(u"Correct Response Data"), default=True)

    def __str__(self):
        return "{} - {}".format(self.response_channel.name, self.record_card.description[:100])

    @property
    def response_destination(self):
        """
        :return: All the response data as one line string
        """
        base_dst = f"{self.via_type} {self.address_mobile_email} {self.number} {self.postal_code}".strip()
        if self.municipality:
            return base_dst + f", {self.municipality}, {self.province}"
        return base_dst

    def is_immediate(self):
        return self.response_channel_id == ResponseChannel.IMMEDIATE

    def get_response_channel(self):
        if self.is_immediate():
            needs_answer = self.record_card.claims_number > 0 or\
                           self.record_card.record_state_id == RecordState.PENDING_ANSWER
            if needs_answer and self.address_mobile_email.strip():
                return ResponseChannel.EMAIL
            return ResponseChannel.NONE
        return self.response_channel_id


class RecordCardTextResponse(UserTrack):
    """
    IRS_TB_RESP_FITXA_TEXT
    """
    RESPONSE_WORKED = "t"
    TEMPLATE_CHANGED = "p"
    OTHERS = "o"

    WORKED_OPTIONS = (
        (RESPONSE_WORKED, _("Response worked")),
        (TEMPLATE_CHANGED, _("Template Changed")),
        (OTHERS, _("Others")),
    )

    record_card = models.ForeignKey(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.PROTECT, db_index=True)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    avoid_send = models.BooleanField(_(u"Avoid send answer"), default=False)
    response = models.TextField(_(u"Response"))
    send_date = models.DateField(_(u"Send Date"))
    text_date = models.DateField(verbose_name=_("Text date"), auto_now_add=True)
    worked = models.CharField(_("Worked"), blank=True, max_length=1, choices=WORKED_OPTIONS)
    record_files = models.ManyToManyField("RecordFile", blank=True, through="record_cards.RecordCardTextResponseFiles")

    def __str__(self):
        return "{} - {} - {}".format(self.record_card.description[:30], self.response[:30], self.send_date)

    @property
    def enabled_record_files(self):
        return [resp_file.record_file for resp_file in self.recordcardtextresponsefiles_set.filter(enabled=True)]


def record_files_path(instance, filename):
    now = timezone.now()
    return "record_files/{}/{}/{}/{}".format(now.year, now.month, now.day, filename)


class RecordFile(UserTrack):
    CREATE = 0
    DETAIL = 1
    COMMUNICATIONS = 2
    WEB = 3
    ANSWER = 4
    IRIS = 5

    TYPES = (
        (CREATE, _("From Record Creation")),
        (DETAIL, _("From Record Detail")),
        (COMMUNICATIONS, _("From Record Communications")),
        (WEB, _("From Public Web")),
        (ANSWER, _("From Response")),
        (IRIS, _("IRIS1")),
    )

    record_card = models.ForeignKey(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.PROTECT, db_index=True)
    file = models.FileField(verbose_name=_("Record File"), upload_to=record_files_path, max_length=250,
                            null=True, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    file_type = models.IntegerField(_("File Type"), choices=TYPES, default=CREATE)

    def __str__(self):
        return "{} - file {}".format(self.record_card.description[:30], self.pk)

    @property
    def delete_url(self):
        return reverse_lazy("private_api:record_cards:record_card_file_delete", kwargs={"pk": self.pk})

    @property
    def can_be_deleted(self):
        if self.file_type == self.WEB:
            return False
        return super().can_be_deleted


class ChunkedUploadMixin:

    @property
    def md5(self, rehash=False):
        if getattr(self, '_md5', None) is None or rehash is True:
            md5 = hashlib.md5()
            self.file.open(mode='rb')
            for chunk in self.file.chunks():
                md5.update(chunk)
                self._md5 = md5.hexdigest()
            self.close_file()
        return self._md5

    @transaction.atomic
    def completed(self, completed_at=timezone.now(), ext=COMPLETE_EXT):
        if ext != INCOMPLETE_EXT:
            original_filename = self.file.name
            self.file.name = os.path.splitext(self.file.name)[0] + ext

            file = default_storage.open(original_filename)
            logger.info('Saving file on real path ' + self.file.name)
            default_storage.save(self.file.name, file)
            logger.info('Deleting original file' + original_filename)
            default_storage.delete(original_filename)
        logger.info('DELETED FILE')
        self.status = self.COMPLETE
        self.completed_at = completed_at
        self.save()

    def delete_file(self):
        if self.file:
            default_storage.delete(self.file.name)
        self.file = None

    def append_chunk(self, chunk, chunk_size=None, save=True):
        logger.info('READ FILE CONTENT')
        file = default_storage.open(self.file.name, mode="rb+")
        file_content = file.read()
        logger.info('APPEND CHUNK')
        for subchunk in chunk.chunks():
            file_content += subchunk

        file.seek(0)
        file.write(file_content)
        logger.info('DELETE OLD CHUNK')
        default_storage.delete(self.file.name)
        logger.info('SAVE CHUNK')
        default_storage.save(self.file.name, file)

        if chunk_size is not None:
            self.offset += chunk_size
        elif hasattr(chunk, 'size'):
            self.offset += chunk.size
        else:
            self.offset = file.size
        self._md5 = None  # Clear cached md5
        if save:
            self.save()
        logger.info('CLOSE')
        self.close_file()  # Flush


class RecordChunkedFile(ChunkedUploadMixin, ChunkedUpload):
    objects = RecordFileManager()

    record_card = models.ForeignKey(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(User, related_name="%(class)s", on_delete=models.CASCADE)
    file_type = models.IntegerField(_("File Type"), choices=RecordFile.TYPES, default=RecordFile.CREATE)

    class Meta:
        ordering = ("-completed_at", "-status", "-created_at",)

    def __str__(self):
        return "{} - file {}".format(self.record_card.description[:30], self.pk)


class RecordCardTextResponseFiles(CleanEnabledBase, UserTrack):
    field_error_name = "record_file"

    text_response = models.ForeignKey(RecordCardTextResponse, on_delete=models.CASCADE)
    record_file = models.ForeignKey(RecordFile, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "text_response": self.text_response,
            "record_file": self.record_file
        }


class RecordCardReasignation(UserTrack):
    objects = RecordCardReasignationManager().as_manager()

    user_id = UserIdField(db_index=True)
    record_card = models.ForeignKey(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.PROTECT, db_index=True)
    group = models.ForeignKey(Group, verbose_name=_("User Group"), on_delete=models.PROTECT)
    previous_responsible_profile = models.ForeignKey(Group, verbose_name=_("Previuos Responsible Group"),
                                                     on_delete=models.PROTECT, related_name="previous_responsible")
    next_responsible_profile = models.ForeignKey(Group, verbose_name=_("Next Responsible Group"),
                                                 on_delete=models.PROTECT, related_name="next_responsible")
    reason = models.ForeignKey(Reason, verbose_name=_("Reason"), on_delete=models.PROTECT)
    comment = models.TextField(_("Comment"))

    def __str__(self):
        return "{} reasigned from {} to {}".format(self.record_card.description[:30],
                                                   self.previous_responsible_profile.description,
                                                   self.next_responsible_profile.description)

    @staticmethod
    def check_different_responsible_profiles(previous_responsible_profile_id, next_responsible_profile_id):
        """
        Check that the previous responsible profile and the new one are different
        :param previous_responsible_profile_id: Previous group responsible id
        :param next_responsible_profile_id: Next group responsible id
        :return:
        """
        if previous_responsible_profile_id == next_responsible_profile_id:
            error_message = _("Previous responsibe profile and next responsible profile can not be the same")
            raise ValidationError({"previous_responsible_profile": error_message,
                                   "next_responsible_profile": error_message})

    @staticmethod
    def check_reasignation_in_allowed_reasignations(record_card, next_responsible_profile, reasigner_group,
                                                    outside_perm=False):
        """
        Check that the next responsible profile reasignation is in the posible reasignations groups. If not, raise error
        :param record_card: RecordCard to be reasignated
        :param next_responsible_profile: Next group responsible
        :param reasigner_group: Group that is creating the reasignation
        :return:
        """
        reassignation_checker = PossibleReassignations(record_card, outside_perm)
        if next_responsible_profile not in reassignation_checker.reasignations(reasigner_group):
            error_message = _("Selected next group responsible of record card is not one of the possible options")
            raise ValidationError({"next_responsible_profile": error_message})

    @staticmethod
    def check_recordcard_reasignment_not_allowed(record_card):
        if record_card.reassignment_not_allowed:
            raise ValidationError({"record_card": _("The selected RecordCard can not be reassigned")})


class MonthIndicator(models.Model):
    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField(_("Year"))
    month = models.PositiveSmallIntegerField(_("Month"), validators=[MinValueValidator(1), MaxValueValidator(12)])

    entries = models.PositiveSmallIntegerField(_("Record Entries"), default=0)
    pending_validation = models.PositiveSmallIntegerField(_("Pending Validation"))
    processing = models.PositiveSmallIntegerField(_("Processing"))
    closed = models.PositiveSmallIntegerField(_("closed"))
    cancelled = models.PositiveSmallIntegerField(_("Cancelled"))
    external_processing = models.PositiveSmallIntegerField(_("External Processing"))
    pending_records = models.PositiveSmallIntegerField(_("Pending records"))
    average_close_days = models.PositiveSmallIntegerField(_("Average Close Days"))
    average_age_days = models.PositiveSmallIntegerField(_("Average Age Days"))

    def __str__(self):
        return "{} - {}/{}".format(self.group.description, self.month, self.year)


class Workflow(UserTrack):
    """
    IRS_TB_PROCES
    """
    main_record_card = models.ForeignKey(RecordCard, verbose_name=_(u"Record Card"), on_delete=models.PROTECT,
                                         db_index=True, related_name="main_record_card")
    state = models.ForeignKey(RecordState, verbose_name=_(u"State"), on_delete=models.PROTECT, db_index=True)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    close_date = models.DateField(_(u"Close Date"), null=True, blank=True)
    visual_user = models.CharField(_(u"Visual User"), blank=True, max_length=50)
    element_detail_modified = models.BooleanField(_(u"Theme modified"), default=False)

    def __str__(self):
        return "{} - {}".format(self.main_record_card.description[:30], self.state)

    def state_change(self, next_state):
        if self.unclosed_records:
            self.state_id = next_state
        else:
            self.close(save=False)
        self.save()

    def close(self, save=True):
        self.state_id = RecordState.CLOSED
        self.close_date = timezone.now().date()
        if save:
            self.save()

    @property
    def unclosed_records(self):
        """
        :return: True if workflow has any record in a not closed state
        """
        return self.recordcard_set.filter(~Q(record_state_id__in=RecordState.CLOSED_STATES)).exists()


class WorkflowPlan(models.Model):
    workflow = models.OneToOneField(Workflow, verbose_name=_("Workflow"), on_delete=models.PROTECT, db_index=True)
    responsible_profile = models.CharField(_(u"Service or person in charge"), max_length=400, blank=True)
    start_date_process = models.DateTimeField(_(u"Start Date Process"), null=True)
    action_required = models.BooleanField(default=True)

    def __str__(self):
        return "{} - {}".format(self.workflow.main_record_card.description[:30], self.start_date_process)

    def save(self, *args, **kwargs):
        self.is_appointment = self.workflow.main_record_card.element_detail.requires_appointment
        super().save(*args, **kwargs)


class WorkflowResolution(models.Model):
    workflow = models.OneToOneField(Workflow, verbose_name=_("Workflow"), on_delete=models.PROTECT, db_index=True)
    service_person_incharge = models.CharField(_(u"Service or person in charge"), max_length=400, blank=True)
    resolution_type = models.ForeignKey(ResolutionType, verbose_name=_(u"Resolution Type"), on_delete=models.PROTECT)
    resolution_date = models.DateTimeField(_(u"Resolution Date"), null=True)
    is_appointment = models.BooleanField(default=False)

    def __str__(self):
        return "{} - {} - {}".format(self.workflow.main_record_card.description[:30], self.resolution_type,
                                     self.resolution_date)

    def save(self, *args, **kwargs):
        self.is_appointment = self.workflow.main_record_card.element_detail.requires_appointment
        super().save(*args, **kwargs)

    @property
    def can_be_deleted(self):
        return True


class WorkflowComment(UserTrack):
    """
    IRS_TB_OBSERVACIO
    """

    PLAN = "p"
    RESOLUTION = "r"

    TASKS = (
        (PLAN, _(u"Planning")),
        (RESOLUTION, _(u"Resolution")),
    )

    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), on_delete=models.PROTECT, db_index=True)
    group = models.ForeignKey(Group, verbose_name=_("Group"), null=True, blank=True, on_delete=models.PROTECT)
    task = models.CharField(_(u"Task"), max_length=20, choices=TASKS)
    enabled = models.BooleanField(_(u"Enabled"), default=True, db_index=True)
    comment = models.TextField(_("Comment"))

    def __str__(self):
        return "{} - {}".format(self.workflow.__str__(), self.comment[:100])

    class Meta:
        ordering = ("-created_at",)


class WorkflowResolutionExtraFields(models.Model):
    """
    Extra fields for Workflow Resolution - IRIS MÒBIL
    """
    workflow_resolution = models.OneToOneField(
        WorkflowResolution, verbose_name=_("Workflow"), on_delete=models.PROTECT, db_index=True
    )
    resolution_date_end = models.DateTimeField(_(u"Resolution Date End"), null=True)
    ubication_start = models.ForeignKey(
        to=Ubication,
        verbose_name=_("Ubication start"),
        null=True, on_delete=models.CASCADE,
        related_name="ubication_start",
    )
    ubication_end = models.ForeignKey(
        to=Ubication,
        verbose_name=_("Ubication end"),
        null=True,
        on_delete=models.CASCADE,
        related_name="ubication_end",
    )
