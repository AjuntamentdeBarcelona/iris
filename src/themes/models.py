from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Max
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from custom_safedelete.managers import CustomSafeDeleteManager
from features.models import Feature
from iris_masters.mixins import CleanEnabledBase
from iris_masters.models import (VISIBILITY_PUBLIC, BasicMaster, RecordType, ResponseChannel,
                                 UserTrack, VisibilityOptionField, Application, Process, RecordState, District,
                                 ExternalService, Parameter)
from main.cachalot_decorator import iris_cachalot
from main.core.models import CaseInsensitiveUniqueMixin

from ordered_model.models import OrderedModelBase

from custom_safedelete.models import CustomSafeDeleteModel
from profiles.models import Group
from themes.managers import ElementDetailFeatureManager, ApplicationElementDetailManager
from themes.tasks import rebuild_theme_tree

DESCRIPTIONS_MAX_LENGTH = 80


class ThemeGroup(CustomSafeDeleteModel, BasicMaster):
    """
    Classifier for the different themes, they are attached to one or more RecordElement instances.

    The description field should not be translated.

    IRS_TB_MA_DETALL_AGRUPACIO
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    description = models.CharField(max_length=60)
    position = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("description", "deleted")


class Area(CaseInsensitiveUniqueMixin, CustomSafeDeleteModel, OrderedModelBase, UserTrack):
    """
    Group for issues and requests according to the different services and topics managed by the town council.

    For example:
    - cleaning
    - mobility
    - citizen support
    :todo: define query_area functionality

    IRS_TB_MA_AREA
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    ENABLED_AREA_FILTERS = {"deleted__isnull": True}
    order_field_name = "order"

    description = models.CharField(max_length=DESCRIPTIONS_MAX_LENGTH, verbose_name=_("Description"))
    area_code = models.CharField(max_length=12, verbose_name=_("Area Code"), blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    query_area = models.BooleanField(default=False, verbose_name=_("Query tree Area"))
    icon_name = models.CharField(max_length=50, verbose_name=_("Icon Name"), blank=True, default="")
    favourite = models.BooleanField(default=False, verbose_name=_("Favourite"))

    class Meta:
        ordering = ("order",)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, keep_deleted=False):
        if not self.area_code:
            self.set_code()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields,
                     keep_deleted=keep_deleted)
        rebuild_theme_tree.delay()

    def __str__(self):
        return self.description

    def set_code(self):
        """
        :return: The code of a new Area is defined as MAX(CODI_AREA) + 1. Max two digits.
        """
        max_code = self.__class__.objects.all_with_deleted().aggregate(last_code=Max('area_code'))
        new_code = '{}'.format(int(max_code['last_code']) + 1) if max_code['last_code'] else '1'
        self.area_code = new_code.zfill(2)
        return self.area_code

    def can_be_deleted(self):
        return not self.areas.filter(deleted__isnull=True).exists()


class Element(CaseInsensitiveUniqueMixin, CustomSafeDeleteModel, OrderedModelBase, UserTrack):
    """
    Concrete service or element of an area affected by an issue or request.

    For example:
    - streetlight (element)
    - dumpster (element)
    - garbage collection (service)
    :todo: icon name help text (which are the possible values?)

    IRS_TB_MA_ELEMENT
    """
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["area_id"])

    ENABLED_ELEMENT_FILTERS = {"deleted__isnull": True, "area__deleted__isnull": True}
    order_field_name = "order"

    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="areas")
    description = models.CharField(max_length=DESCRIPTIONS_MAX_LENGTH)
    alternative_text = models.CharField(max_length=600)
    element_code = models.CharField(max_length=36, verbose_name=_("Element Code"), blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_favorite = models.BooleanField(default=False, verbose_name=_("Favorite"))
    icon_name = models.CharField(max_length=50, verbose_name=_("Icon Name"), blank=True, default="")

    class Meta:
        unique_together = ("area", "description", "deleted")
        ordering = ("order",)

    def __str__(self):
        return self.description

    def save(self, keep_deleted=False, **kwargs):
        if not self.element_code:
            self.set_code()
        super().save(keep_deleted, **kwargs)
        rebuild_theme_tree.delay()

    def set_code(self):
        """
        :return: The code of a new Element is defined as CODI_AREA + (MAX(CODI_ELEMENT)) + 1. Max 4 digits.
        """
        max_code = self.area.areas.all_with_deleted().aggregate(last_code=Max('element_code'))
        if max_code['last_code']:
            max_code = max_code['last_code'][2:]
            next_code = '{}'.format(int(max_code) + 1).zfill(2)
            self.element_code = '{}{}'.format(self.area.area_code, next_code)
        else:
            self.element_code = '{}00'.format(self.area.area_code)
        return self.element_code

    def can_be_deleted(self):
        return not self.elements.filter(deleted__isnull=True).exists()


class ElementDetail(OrderedModelBase, CustomSafeDeleteModel, UserTrack):
    """
    Motivation or reason for creating an issue or request related to an element. In other words, the ElementDetails
    defines the attributes that make the difference between two issues for the element. Two different element details
    may need a different flow of resolution, even if they refer to the same element.

    For example:
    - Broken streetlight
    - Overflown dumpster.
    :todo: detail code is seen on page 181 of "Plec Tecnic" but is no listed on fields
    :todo: define the max value needed for similarity meters
    :todo: define if published_at is a DateTimeField or a DateField

    IRS_TB_MA_DETALL
    """
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["element_id"])

    ENABLED_ELEMENTDETAIL_FILTERS = {"deleted__isnull": True, "element__deleted__isnull": True,
                                     "element__area__deleted__isnull": True}
    ACTIVE_MANDATORY_FIEDLS = ["element", "description_gl", "description_es", "description_en",
                               "process", "record_type", ]
    RELATION_ACTIVE_MANDATORY = ["elementdetailresponsechannel_set"]

    order_field_name = "order"

    updated_at = models.DateTimeField(verbose_name=_("Last update"), auto_now=True, db_index=True)

    # TODO: As process is a new field on an existent model, it can not be required.
    # TODO: When we got the data, we can make a data migration and set the field to null=False or to set a default
    process = models.ForeignKey(Process, on_delete=models.PROTECT, verbose_name=_(u"Process"), null=True, blank=False)
    element = models.ForeignKey(Element, on_delete=models.PROTECT, related_name="elements")
    detail_code = models.CharField(max_length=36, verbose_name=_("Detail code"), blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    deleted = models.DateTimeField(null=True, blank=True, editable=False, help_text=_("Deletion date"))

    short_description = models.CharField(max_length=DESCRIPTIONS_MAX_LENGTH, blank=True, default="")
    description = models.TextField(default="")
    pda_description = models.CharField(max_length=255, help_text=_("Description shown on PDA"),
                                       blank=True, default="")
    app_description = models.CharField(max_length=255, help_text=_("Description shown on APP"),
                                       default="", blank=True)

    rat_code = models.CharField(max_length=90, blank=True, default="")
    similarity_hours = models.PositiveSmallIntegerField(
        null=True,
        help_text=_("Maximum time, expressed in hours, between the creation time of two record cards for "
                    "considering them similar"))
    similarity_meters = models.PositiveIntegerField(
        null=True,
        help_text=_("Maximum distance, expressed in meters, between the ubications of two record cards for "
                    "considering them similar."))
    app_resolution_radius_meters = models.PositiveIntegerField(
        null=True,
        help_text=_("Maximum distance starting from the record card ubication, expressed in meters, in which an "
                    "operator can resolve the task using the IRIS smartphone app."))
    sla_hours = models.PositiveSmallIntegerField(
        null=True,
        help_text=_("Maximum hours in which the town council commits to resolve an issues belonging this theme."))
    record_type = models.ForeignKey(RecordType, on_delete=models.PROTECT, null=True,
                                    verbose_name=_("Record type"),
                                    help_text=_("Limit this detail to records of this type."))

    autovalidate_records = models.BooleanField(
        default=False, verbose_name=_("Autovalidate records"),
        help_text=_("If checked, the record cards will be validated automatically on its creation.")
    )
    requires_citizen = models.BooleanField(
        default=False, verbose_name=_("Requires Citizen"),
        help_text=_("If checked, the citizen data will be required for creating a record card.")
    )
    requires_ubication = models.BooleanField(
        default=False, verbose_name=_("Requires Ubication"),
        help_text=_("If checked, an address will be required as ubication for creating a record card.")
    )
    # TODO: review field as its not used
    requires_ubication_full_address = models.BooleanField(
        default=False, verbose_name=_("Requires full address"),
        help_text=_("If checked, a full adress with floor and door will be required as ubication for "
                    "creating a record card.")
    )
    requires_ubication_district = models.BooleanField(
        default=False, verbose_name=_("Requires District Ubication"),
        help_text=_("If checked, a district will be required as ubication for creating a record card.")
    )
    aggrupation_first = models.BooleanField(
        default=False, verbose_name=_("Aggrupation first"),
        help_text=_("If checked, the aggrupation data will be selected as default on the website.")
    )
    immediate_response = models.BooleanField(
        default=False, verbose_name=_("Immediate response"),
        help_text=_("If checked, the response to the record will be required on its creation")
    )
    first_instance_response = models.BooleanField(
        default=False, verbose_name=_("First instance response"),
        help_text=_("If checked, a first instance response will be given for the record cards belonging to this theme.")
    )
    requires_appointment = models.BooleanField(
        default=False, verbose_name=_("Requires Appointment"),
        help_text=_("If checked, an appointment will be required for creating records for this theme.")
    )
    allow_resolution_change = models.BooleanField(
        default=False, verbose_name=_("Allow theme change on resolution"),
        help_text=_("If checked, the records belonging to this theme could change its theme on resolution.")
    )
    validated_reassignable = models.BooleanField(
        default=True, verbose_name=_("Allow reassignment even if validated"),
        help_text=_("If checked, the record could be reassigned even if validated.")
    )
    sla_allows_claims = models.BooleanField(
        default=False, verbose_name=_("Allow claims on SLA time"),
        help_text=_("If checked, claims could be created on the SLA time.")
    )
    allow_external = models.BooleanField(
        default=False, verbose_name=_("Created by external system"),
        help_text=_("If true, the record cards of this theme must be created by external systems.")
    )
    custom_answer = models.BooleanField(
        default=False, verbose_name=_("Custom answer"),
        help_text=_("If true, the operator must write a custom answer for each record type of the theme.")
    )
    show_pda_resolution_time = models.BooleanField(
        default=False, verbose_name=_("Show PDA resolution time"),
    )
    allow_multiderivation_on_reassignment = models.BooleanField(
        default=False, verbose_name=_("Allow multiderivation on reassignment"),
    )

    visibility = VisibilityOptionField(default=VISIBILITY_PUBLIC)
    validation_place_days = models.PositiveSmallIntegerField(
        null=True,
        help_text=_("Max number of days for validating a record card, modify the theme or reassign outside its "
                    "environment.")
    )

    published_at = models.DateField(null=True, blank=True, verbose_name=_("Publication date"))
    features = models.ManyToManyField(Feature, blank=True,
                                      through="themes.ElementDetailFeature")
    response_channels = models.ManyToManyField(ResponseChannel, blank=True,
                                               through="themes.ElementDetailResponseChannel")
    groups = models.ManyToManyField(ThemeGroup, blank=True, through="themes.ElementDetailThemeGroup")
    external_protocol_id = models.CharField(max_length=48, blank=True, default="", verbose_name=_("Protocol ID"),
                                            help_text=_("Itaca ID for the desired protocol."))

    # Templates
    email_template = models.TextField(blank=True, default="")
    sms_template = models.CharField(max_length=480, blank=True, default="")

    # Open data
    allows_open_data = models.BooleanField(default=False, verbose_name=_("Show on Open Data"),
                                           help_text=_("Records from this theme could be shown on Open Data portal."))
    allows_open_data_location = models.BooleanField(default=False, verbose_name=_("Location on Open Data"),
                                                    help_text=_("Records will shown its location on Open Data portal."))
    allows_open_data_sensible_location = models.BooleanField(
        default=False,
        verbose_name=_("Sensible Location on Open Data (Only census section)"),
        help_text=_("Records will shown sensible locations on Open Data portal."))

    # SSI
    allows_ssi = models.BooleanField(default=False, verbose_name=_("Show on SSI"),
                                     help_text=_("Records from this theme could be shown on SSI."))
    allows_ssi_location = models.BooleanField(default=False, verbose_name=_("Location on Open Data"),
                                              help_text=_("Records will shown its location on SSI."))
    allows_ssi_sensible_location = models.BooleanField(
        default=False,
        verbose_name=_("Sensible Location on SSI (Only census section)"),
        help_text=_("Records will shown sensible locations on SSI."))

    head_text = models.TextField(verbose_name=_("Head text"), default="", blank=True)
    footer_text = models.TextField(verbose_name=_("Footer text"), default="", blank=True)
    links = models.TextField(verbose_name=_("Links"), default="", blank=True)
    lopd = models.TextField(verbose_name=_("GDPR"), default="", blank=True)

    # application M2M
    applications = models.ManyToManyField(Application, through="themes.ApplicationElementDetail", blank=True)
    external_service = models.ForeignKey(ExternalService, null=True, blank=True, on_delete=models.SET_NULL,
                                         help_text=_("Validate and manage by sending the card to an external service"))
    external_email = models.EmailField(blank=True, default="")

    active = models.BooleanField(default=False, verbose_name=_("Active"), db_index=True,
                                 help_text=_("If checked, the theme can be used in RecordCard creation"))
    activation_date = models.DateField(_("Activation Date"), null=True, blank=True, db_index=True,
                                       help_text=_("Date from which the theme will be active"))
    visible = models.BooleanField(default=False, verbose_name=_("Visible"), db_index=True,
                                  help_text=_("If checked, the theme can be shown in theme tree"))
    visible_date = models.DateField(_("Visible Date"), null=True, blank=True, db_index=True,
                                    help_text=_("Date from which the theme will be visible"))
    average_close_days = models.PositiveSmallIntegerField(_("Average Close Days"), null=True, blank=True,
                                                          help_text=_("Average of days to close records of this theme."
                                                                      "Null if it's not calculated"))
    group_profiles = models.ManyToManyField(Group, through="themes.GroupProfileElementDetail", blank=True)
    pend_commmunications = models.BooleanField(_("Pending communications notifications"), default=True,
                                               help_text=_("Send reminder of pending notifications on communications"))
    allow_english_lang = models.BooleanField(default=False, verbose_name=_("Allow english language"),
                                             help_text=_("If checked, allows to select english as the language "
                                                         "of the response"))

    class Meta:
        unique_together = ("element", "short_description", "deleted")
        ordering = ("order",)

    def save(self, *args, **kwargs):
        if not self.detail_code:
            self.set_code()
        super().save(*args, **kwargs)
        rebuild_theme_tree.delay()

    def set_code(self):
        """
        :return: Codi detall => area_code(2 digits) + element_code (2digits) + detail_code (two digits)
        """
        max_code = self.element.elements.all_with_deleted().aggregate(last_code=Max('detail_code'))
        if max_code['last_code']:
            max_code = max_code['last_code'][4:]
            new_code = '{}'.format(int(max_code) + 1).zfill(2)
            self.detail_code = '{}{}'.format(self.element.element_code, new_code)
        else:
            self.detail_code = '{}00'.format(self.element.element_code)
        return self.detail_code

    @property
    def ans_delta_hours(self):
        if self.sla_hours:
            return self.sla_hours
        return int(Parameter.get_parameter_by_key("DIES_ANS_DEFECTE", 30)) * 24

    @property
    def can_be_deleted(self):
        return True

    @property
    def is_active(self):
        if not self.active:
            return False
        if not self.activation_date:
            return True
        return True if self.activation_date <= timezone.now().date() else False

    @property
    def is_visible(self):
        if not self.is_active or not self.visible:
            return False
        if not self.visible_date:
            return True
        return True if self.visible_date <= timezone.now().date() else False

    @cached_property
    def has_group_profiles(self):
        return self.groupprofileelementdetail_set.filter(enabled=True).exists()

    def group_can_see(self, group_plate):
        return self.groupprofileelementdetail_set.filter(
            enabled=True, group__group_plate__startswith=group_plate).exists()

    @staticmethod
    def check_external_protocol_with_immediate_response(immediate_response, external_protocol_id):
        if immediate_response and not external_protocol_id:
            raise ValidationError(
                {"external_protocol_id": _("If inmmediate response is True, this field is required!")})

    def clean(self):
        super().clean()
        self.check_external_protocol_with_immediate_response(self.immediate_response, self.external_protocol_id)

    def register_theme_ambit(self):
        """
        Register the ambits of a theme
        :return:
        """

        theme_ambits = []

        with transaction.atomic():
            # Delete previous ambits
            ElementDetailGroup.objects.filter(element_detail_id=self.pk).delete()

            # Get ambit from derivations
            self.get_ambit_from_derivation(theme_ambits, "derivationdirect_set")
            self.get_ambit_from_derivation(theme_ambits, "derivationdistrict_set")

            # If there are ambits, register it with a bulk operation
            if theme_ambits:
                ElementDetailGroup.objects.bulk_create(
                    ElementDetailGroup(element_detail=self, **ambit_group) for ambit_group in theme_ambits)

    def get_ambit_from_derivation(self, theme_ambits, derivations_related):
        """
        Get the ambit group from a derivation type
        :param theme_ambits: list of ambits
        :param derivations_related: type of derivation
        :return:
        """
        for derivation in getattr(self, derivations_related).filter(
                record_state=RecordState.PENDING_VALIDATE, enabled=True
        ).select_related("group"):
            for ambit_group in derivation.group.get_ancestors(include_self=True):
                if ambit_group not in theme_ambits:
                    theme_ambits.append({
                        'group_id': ambit_group.id,
                        'district_id': getattr(derivation, 'district_id', None)
                    })


class ElementDetailFeature(CleanEnabledBase, OrderedModelBase, UserTrack):
    """
    IRS_TB_MA_TEMATICA_ATRIBUTS

    Each theme (ElementDetail) may need or require additional data for n features when a new record card is created.
    This features can be special (always mandatory) or normal (mandatory or optional).
    """
    objects = iris_cachalot(ElementDetailFeatureManager(),
                            extra_fields=["element_detail_id", "feature_id", "is_mandatory"])
    order_field_name = "order"
    field_error_name = "feature"

    element_detail = models.ForeignKey(ElementDetail, on_delete=models.CASCADE, related_name="feature_configs")
    feature = models.ForeignKey(Feature, on_delete=models.PROTECT, related_name="element_configs")
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    is_mandatory = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=100, db_index=True)

    class Meta:
        ordering = ("order",)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.feature.is_special:
            self.is_mandatory = True
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return "{} - {}".format(self.element_detail.element.description, self.feature.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "element_detail": self.element_detail,
            "feature": self.feature
        }


class Keyword(CleanEnabledBase, UserTrack):
    """
    Keywords for ElementDetail

    IRS_TB_MA_PARAULES_CLAU
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["detail_id"])

    field_error_name = "description"

    detail = models.ForeignKey(ElementDetail, on_delete=models.CASCADE)
    description = models.CharField(verbose_name=_("Description"), max_length=40)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    class Meta:
        index_together = ("detail", "description", "enabled")

    def __str__(self):
        return self.description

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.description = self.description.upper()
        super().save(force_insert, force_update, using, update_fields)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "description": self.description,
            "detail": self.detail
        }


class ApplicationElementDetail(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_SISTEMA_DETALL
    """
    objects = iris_cachalot(ApplicationElementDetailManager(), extra_fields=["detail_id", "application_id"])
    field_error_name = "application"

    detail = models.ForeignKey(ElementDetail, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    favorited = models.BooleanField(verbose_name=_("Favorited"), default=False)

    def __str__(self):
        return "{} - {}".format(self.detail.detail_code, self.application.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "detail": self.detail,
            "application": self.application
        }


class GroupProfileElementDetail(CleanEnabledBase, UserTrack):
    field_error_name = "group"

    element_detail = models.ForeignKey(ElementDetail, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_(u"Group"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "{} - {}".format(self.element_detail.detail_code, self.group.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "element_detail": self.element_detail,
            "group": self.group
        }


class DerivationDirect(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_MULTI_DERIVACIO
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["element_detail_id", "record_state_id", "derivation_type"])

    field_error_name = "record_state"

    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.CASCADE)
    record_state = models.ForeignKey(RecordState, verbose_name=_(u"Record State"), on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_(u"Group"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    derivation_type = models.CharField(_(u"Derivation Type"), max_length=3, blank=True)  # TODO: select?

    def __str__(self):
        return "{} - {}".format(self.element_detail.short_description, self.group.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "element_detail": self.element_detail,
            "record_state": self.record_state,
        }


class DerivationDistrict(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_DIST_DET_PER
    """
    objects = iris_cachalot(models.Manager(),
                            extra_fields=["element_detail_id", "record_state_id", "district_id", "group_id"])
    field_error_name = "record_state"

    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.CASCADE)
    record_state = models.ForeignKey(RecordState, verbose_name=_(u"Record State"), on_delete=models.CASCADE,
                                     default=RecordState.PENDING_VALIDATE)
    district = models.ForeignKey(District, verbose_name=_(u"District"), on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_(u"Group"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "{} - {} - {}".format(self.element_detail.short_description, self.district.name,
                                     self.group.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "element_detail": self.element_detail,
            "record_state": self.record_state,
            "district": self.district,
        }


class Zone(CustomSafeDeleteModel, BasicMaster):
    """
    IRS_TB_MA_TIPUS_ZONA
    """
    CARRCENT_PK = 1
    SENYAL_VERTICAL_PK = 2
    codename = models.CharField(verbose_name=_("Codename"), max_length=20, db_index=True, blank=False, unique=True)
    description = models.CharField(verbose_name=_("Description"), max_length=60, unique=True)


class DerivationPolygon(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_ZONA_PERFIL
    """
    field_error_name = "polygon_code"
    zone = models.ForeignKey(Zone, verbose_name=_(u"Zone"), on_delete=models.CASCADE)
    polygon_code = models.CharField(_("Polygon Code"), max_length=100)
    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.CASCADE)
    district_mode = models.BooleanField(default=False)
    record_state = models.ForeignKey(RecordState, verbose_name=_(u"Record State"), on_delete=models.CASCADE,
                                     default=RecordState.PENDING_VALIDATE)
    group = models.ForeignKey(Group, verbose_name=_(u"Group"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "zone": self.zone,
            "polygon_code": self.polygon_code,
            "element_detail": self.element_detail,
            "record_state": self.record_state
        }

    class Meta:
        ordering = ('polygon_code',)


class ElementDetailResponseChannel(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_CANAL_RESP_TIPUS
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["elementdetail_id", "responsechannel_id"])
    field_error_name = "responsechannel"

    elementdetail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.CASCADE)
    responsechannel = models.ForeignKey(ResponseChannel, verbose_name=_(u"Response Channel"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    application = models.ForeignKey(Application, verbose_name=_(u"Application"), on_delete=models.CASCADE,
                                    default=Application.IRIS_PK)

    class Meta:
        db_table = "themes_elementdetail_response_channels"

    def __str__(self):
        return "{} - {} - {}".format(self.elementdetail.short_description, self.responsechannel.name,
                                     self.application.description)

    @staticmethod
    def check_none_responsechannel_with_immediate_response(element_detail, response_channel):
        if not element_detail.immediate_response and response_channel.pk == ResponseChannel.NONE:
            raise ValidationError(
                {"responsechannel": _("ResponseChannel None is not valid for a no immediate response theme")})

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "elementdetail": self.elementdetail,
            "responsechannel": self.responsechannel,
            "application": self.application
        }


class ElementDetailThemeGroup(CleanEnabledBase, UserTrack):
    field_error_name = "theme_group"
    objects = iris_cachalot(models.Manager(), extra_fields=["element_detail_id", "theme_group_id"])

    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.CASCADE)
    theme_group = models.ForeignKey(ThemeGroup, verbose_name=_(u"Theme Group"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            "element_detail": self.element_detail,
            "theme_group": self.theme_group
        }


class ElementDetailGroup(models.Model):
    """
    Model to register ElementDetail ambits
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["element_detail_id", "group_id"])

    element_detail = models.ForeignKey(ElementDetail, verbose_name=_(u"Element Detail"), on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_(u"Group"), on_delete=models.CASCADE, db_index=True)
    district = models.ForeignKey(District, null=True, blank=True, on_delete=models.PROTECT, db_index=True)

    def __str__(self):
        return "{} - {}".format(self.element_detail.description, self.group.description)


class ElementDetailDeleteRegister(UserTrack):
    """
    Model to register element detail's deletion and control the state of the deletion process
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    deleted_detail = models.ForeignKey(ElementDetail, on_delete=models.CASCADE, related_name="deleted_details")
    reasignation_detail = models.ForeignKey(ElementDetail, on_delete=models.CASCADE,
                                            related_name="reasignation_details")
    only_open = models.BooleanField(_("Only Open RecordCards"), default=True)
    process_finished = models.BooleanField(_("Process finished"), default=False,
                                           help_text=_("Shows if RecordCard details reassignations "
                                                       "has finished correctly"))
