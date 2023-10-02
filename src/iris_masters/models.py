from django.conf import settings
from django.contrib.auth.models import User
from django.core.signing import Signer
from django.db import models
from django.utils.translation import gettext_lazy as _

from custom_safedelete.managers import CustomSafeDeleteManager
from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.mixins import CleanEnabledBase, CleanSafeDeleteBase
from main.cachalot_decorator import iris_cachalot


class UserIdField(models.CharField):
    """
    Custom model field for storing the User id references.
    """
    DEFAULT_LENGTH = 291

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', self.DEFAULT_LENGTH)
        super().__init__(verbose_name=kwargs.pop("verbose_name", _("User ID")), *args, **kwargs)


class UserTrack(models.Model):
    user_id = UserIdField()
    created_at = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name=_("Last update"), auto_now=True)

    class Meta:
        abstract = True

    @property
    def can_be_deleted(self):
        return True


class BasicMaster(UserTrack):
    description = models.CharField(verbose_name=_("Description"), max_length=40, unique=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.description


TYPE_ISSUE = "i"
TYPE_COMPLAINT = "c"
TYPE_SUGGESTION = "s"
TYPE_GRATITUDE = "g"
TYPE_SERVICE_RQ = "r"
TYPE_QUERY = "q"
RECORD_TYPES = {
    TYPE_ISSUE: _("Incidència"),
    TYPE_COMPLAINT: _("Queixa"),
    TYPE_SUGGESTION: _("Suggeriment"),
    TYPE_GRATITUDE: _("Agraïment"),
    TYPE_SERVICE_RQ: _("Petició de servei"),
    TYPE_QUERY: _("Consulta"),
}


class RecordType(BasicMaster):
    """
    All the RecordCards have a type in function of its purpose. These types are: issue, complaint, suggestion, thanks,
    service request or query.

    IRS_TB_MA_TIPUS_FITXA
    """
    objects = iris_cachalot(models.Manager())

    SUGGESTION = 2
    SERVICE_REQUEST = 4
    QUERY = 5

    tri = models.SmallIntegerField(verbose_name=_("TRI"))
    trt = models.SmallIntegerField(verbose_name=_("TRT"))

    @property
    def can_be_deleted(self):
        # RecordTypes can only be listed, read and updated on the api
        return False


class ResponseType(CustomSafeDeleteModel, UserTrack):
    """
    Model to register the responses type
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    description = models.CharField(_(u"description"), max_length=60)

    class Meta:
        unique_together = ("description", "deleted")

    def __str__(self):
        return self.description

    @property
    def can_be_deleted(self):
        return not self.iristemplate_set.exists()


class RecordState(CleanEnabledBase, UserTrack):
    """
    All the RecordCards have an state. States are: pending to validate, in planning, in resolution, pending answer,
    closed, cancelled, not processed, external processing

    IRS_TB_MA_ESTAT_FITXA
    """
    field_error_name = "description"

    PENDING_VALIDATE = 0
    IN_PLANING = 1

    IN_RESOLUTION = 2
    PENDING_ANSWER = 3
    CLOSED = 4
    CANCELLED = 5
    NO_PROCESSED = 6
    EXTERNAL_PROCESSING = 7
    EXTERNAL_RETURNED = 8
    STATES_IN_PROCESSING = [IN_PLANING, IN_RESOLUTION, PENDING_ANSWER]
    PEND_VALIDATE_STATES = [PENDING_VALIDATE, EXTERNAL_RETURNED]
    OPEN_STATES = [PENDING_VALIDATE, IN_PLANING, IN_RESOLUTION, PENDING_ANSWER, NO_PROCESSED, EXTERNAL_RETURNED]
    CLOSED_STATES = [CLOSED, CANCELLED, NO_PROCESSED, EXTERNAL_PROCESSING]
    DEF_CLOSED_STATES = [CLOSED, CANCELLED, EXTERNAL_PROCESSING]
    VALIDATE_STATES = [IN_PLANING, IN_RESOLUTION, PENDING_ANSWER, EXTERNAL_PROCESSING, CLOSED]

    STATES = (
        (PENDING_VALIDATE, _(u"Pending to be validated")),
        (IN_PLANING, _(u"Planned")),
        (IN_RESOLUTION, _(u"In solution")),
        (PENDING_ANSWER, _(u"Pending to give a reply")),
        (CLOSED, _(u"Closed")),
        (CANCELLED, _(u"Canceled")),
        (NO_PROCESSED, _(u"Not processed")),
        (EXTERNAL_PROCESSING, _(u"Externally processed")),
        (EXTERNAL_RETURNED, _(u"External returned")),
    )

    ACRONYMS = {
        PENDING_VALIDATE: "PEND",
        IN_PLANING: "PLAN",
        IN_RESOLUTION: "RES",
        PENDING_ANSWER: "P RESP",
        CLOSED: "TANC",
        CANCELLED: "ANUL",
        NO_PROCESSED: "NO TRAM",
        EXTERNAL_PROCESSING: "T EXT",
        EXTERNAL_RETURNED: "RE EXT",
    }

    id = models.PositiveIntegerField(verbose_name=_(u"ID"), primary_key=True, unique=True, choices=STATES)
    description = models.CharField(verbose_name=_("Description"), max_length=40)
    acronym = models.CharField(verbose_name=_("Acronym"), max_length=10, blank=True)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return self.description

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"description": self.description}


class Reason(CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_MA_MOTIU
    """
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["reason_type"])

    FALSE_ERRONEOUS_DATA = 0
    DUPLICITY_REPETITION = 1
    DISRECPECTFUL_UNINTELLIGIBLE = 2
    THEME_MISTAKE = 3
    COMPUTATIONS_CHANGE = 4
    COMPUTATIONS_OTHER_ADMIN = 5
    CITIZEN_REQUEST = 6
    INTERNAL_TRANSFER = 7
    BUNKS_NO_ANSWER = 8
    PAINTED_PRIVATE_SECTOR = 9
    NOT_APPLICABLE = 10
    COORDINATOR_EVALUATION = 12
    REASSIGNMENT_OTHER_ADMINS = 13
    BREAKE_DOWN_MULTI = 14

    RECORD_REOPEN = 16
    EXPIRATION = 17
    THEME_CHANGE = 19

    NO_IRIS = 22
    REASSIGNMENT_UNEXPLAINED = 23
    INCORRECT_REASIGNATION = 24
    DAIR_CORRECTION = 25
    VALIDATION_BY_ERROR = 26

    OBSERVATION = 90  # previous id "-2"
    CITIZEN_COMUNICATION = 91  # previous id "-1"
    CITIZEN_RESPONSE = 92  # previous id "-3"

    RECORDCARD_URGENCY_CHANGE = 100
    RECORDCARD_BLOCK_CHANGE = 200
    RECORDCARD_EXTERNAL_RETURN = 300
    RECORDCARD_EXTERNAL_CANCEL = 400
    RECORDCARD_EXTERNAL_CLOSE = 500
    FEATURES_THEME_NO_VISIBLES = 600
    GROUP_DELETED = 700
    RECORDFILE_DELETED = 800
    RECORDCARD_UPDATED = 900
    RECORDCARD_TWITTER = 996
    RECORDCARD_NO_ANSWER = 997
    RECORDCARD_CANCEL_REQUEST = 1000
    RECORDCARD_AUTOMATICALLY_CLOSED = 1100
    RECORDFILE_COPIED = 1200
    DERIVATE_RESIGNATION = 1300
    INITIAL_ASSIGNATION = 1299
    COPY_FILES = 1301
    THEME_DELETED = 1400
    RECORDCARD_RESEND_ANSWER = 1500
    RECORDCARD_INVALID_MAIL = 1600
    GEST_ACTIUS_ERROR = 1700
    CLAIM_CITIZEN_REQUEST = 1800

    AUTOMATIC_REASIGNATIONS_REASONS = [DERIVATE_RESIGNATION, INITIAL_ASSIGNATION, GROUP_DELETED]

    TYPE_0 = "0"
    TYPE_1 = "1"  # cancel
    TYPE_2 = "2"  # reasig
    TYPE_3 = "3"  # reasing on theme change
    TYPE_4 = "4"  # New reasons created

    REASON_TYPES = (
        (TYPE_0, TYPE_0),
        (TYPE_1, TYPE_1),
        (TYPE_2, TYPE_2),
        (TYPE_3, TYPE_3),
        (TYPE_4, TYPE_4)
    )

    description = models.CharField(verbose_name=_("Description"), max_length=100)
    reason_type = models.CharField(verbose_name=_("Reason type"), max_length=1, choices=REASON_TYPES)

    def __str__(self):
        return self.description

    class Meta:
        unique_together = ("description", "deleted")


class MediaType(BasicMaster):
    """
    IRS_TB_MA_TIPUS_MITJA
    """
    objects = iris_cachalot(models.Manager())

    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)


class CommunicationMedia(BasicMaster, CustomSafeDeleteModel):
    """
    IRS_TB_MA_MITJA_COMUNICACIO
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    description = models.CharField(verbose_name=_("Description"), max_length=40)
    input_channel = models.ForeignKey("iris_masters.InputChannel", on_delete=models.CASCADE, null=True, blank=False)
    media_type = models.ForeignKey(MediaType, on_delete=models.CASCADE, null=True, blank=False)

    class Meta:
        unique_together = ("description", "deleted")


class Announcement(CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_ANUNCI
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    title = models.CharField(verbose_name=_("Title"), max_length=50)
    description = models.CharField(verbose_name=_("Description"), max_length=280)
    expiration_date = models.DateTimeField(null=True, blank=True, help_text=_("Expiration date"))
    important = models.BooleanField(verbose_name=_("Important"), default=False)
    seen_by = models.ManyToManyField(verbose_name=_("Seen by"), to=User, blank=True)
    xaloc = models.BooleanField(verbose_name=_("Xaloc"), default=False)

    def __str__(self):
        return self.title[:25]

    def seen(self, user):
        return self.seen_by.filter(id=user.id).exists()


VISIBILITY_PUBLIC = "p"
VISIBILITY_RESPONSIBLE = "r"
VISIBILITY_CONCRETE = "c"

PROFILE_VISIBILITY_OPTIONS = {
    VISIBILITY_PUBLIC: _("Visible for all the profiles"),
    VISIBILITY_RESPONSIBLE: _("Visible for the profiles responsible for the theme's area"),
    VISIBILITY_CONCRETE: _("Visible for the profiles responsible for the theme's area and a "
                           "set of profiles for a concrete areas"),
}


class VisibilityOptionField(models.CharField):
    """
    Custom model field for storing the visibility option of a model.
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_length", 1)
        kwargs.pop("choices", [])
        super().__init__(verbose_name=kwargs.pop("verbose_name", _("Visibility options")), max_length=1,
                         choices=PROFILE_VISIBILITY_OPTIONS.items(), *args, **kwargs)


class ResponseChannel(UserTrack):
    """
    Each response channel represents a way the Town Council has for communicating with a citizen using the system.
    Since a channel could have an implementation for sending messages, for example mailing, each is created by
    the application according to these implementations. The channels shouldn"t be created by end users or using the
    admin. So, the response channel is implemented as a model for simplifying some implementations and take the profits
    of the referential integrity offered by the DBMS.

    IRS_TB_MA_CANALS_RESPOSTA
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["id"])

    EMAIL = 0
    SMS = 1
    LETTER = 2
    NONE = 3
    IMMEDIATE = 4
    TELEPHONE = 5

    IMMEDAIATE_RESPONSE_CHANNELS = [NONE, EMAIL]
    NON_RESPONSE_CHANNELS = [NONE]
    ALLOW_ATTACHMENTS_CHANNELS = [EMAIL, LETTER]

    RESPONSE_TYPES = (
        (EMAIL, _(u"Email")),
        (SMS, _(u"Sms")),
        (LETTER, _(u"Letter")),
        (NONE, _(u"None")),
        (IMMEDIATE, _(u"Immediate")),
        (TELEPHONE, _(u"Telephone")),
    )
    id = models.IntegerField(verbose_name=_(u"ID"), primary_key=True, unique=True, choices=RESPONSE_TYPES)
    name = models.CharField(max_length=20)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    order = models.PositiveIntegerField(default=100, db_index=True)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return self.name


class InputChannel(CleanSafeDeleteBase, BasicMaster, CustomSafeDeleteModel):
    """
    Channel for receiving new record cards or issues.

    For example:
    - Phone
    - Internet
    - PDA

    IRS_TB_MA_CANAL_ENTRADA
    """
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["visible", "can_be_mayorship"])

    field_error_name = "description"
    IRIS = 1
    RECLAMACIO_INTERNA = 73
    ALTRES_CANALS = 68
    QUIOSC = 59
    GABINET_ALCALDIA = 13

    description = models.CharField(verbose_name=_("Description"), max_length=40)
    order = models.PositiveIntegerField(default=0, db_index=True)
    # field to indicate That the InputChannel can be shown at the RecordCard creation
    visible = models.BooleanField(default=True)
    supports = models.ManyToManyField("iris_masters.Support", through="iris_masters.InputChannelSupport", blank=True)
    applicant_types = models.ManyToManyField("iris_masters.ApplicantType", blank=True,
                                             through="iris_masters.InputChannelApplicantType")
    can_be_mayorship = models.BooleanField(default=False, help_text="Input Channel can be use to mayorship")

    def __str__(self):
        return self.description

    class Meta:
        ordering = ("order",)
        unique_together = ("description", "deleted")

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"description": self.description}


class Parameter(UserTrack):
    """
    IRS_TB_MA_PARAMETRES
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["show", "visible", "category"])

    OTHERS = 0
    MANAGEMENT = 1
    SUPPORT = 2
    TEMPLATES = 8
    RECORDS = 3
    WEB = 4
    INTEGRATIONS = 5
    REPORTS = 6
    CREATE = 7
    DEVELOPMENT = 10
    DEPRECATED = 100

    CATEGORIES = (
        (OTHERS, _(u"Others")),
        (CREATE, _(u"Record card create")),
        (MANAGEMENT, _(u"Management")),
        (SUPPORT, _(u"Support")),
        (RECORDS, _(u"Records")),
        (WEB, _(u"Web")),
        (INTEGRATIONS, _(u"Integrations")),
        (REPORTS, _(u"Reports")),
        (DEPRECATED, _(u"Deprecated")),
        (TEMPLATES, _(u"Templates")),
        (DEVELOPMENT, _(u"Desarrollo")),
    )

    parameter = models.CharField(max_length=60, unique=True)
    valor = models.TextField()
    description = models.TextField(blank=True)
    name = models.CharField(max_length=400)
    original_description = models.TextField()
    show = models.BooleanField(default=True, db_index=True)
    data_type = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)  # field to indicate which parameters are visible at the front
    category = models.PositiveSmallIntegerField(choices=CATEGORIES, default=OTHERS)  # field to categorize parameters

    def __str__(self):
        return self.parameter

    @staticmethod
    def get_parameter_by_key(parameter_key, default_value=None):
        try:
            return Parameter.objects.get(parameter=parameter_key).valor
        except Parameter.DoesNotExist:
            return default_value

    @classmethod
    def get_config_dict(cls, param_keys):
        return {p.parameter: p.valor for p in cls.objects.filter(parameter__in=param_keys)}

    @staticmethod
    def max_claims_number():
        return int(Parameter.get_parameter_by_key("FITXES_PARE_RESPOSTA", 5))


class Application(UserTrack):
    """
    Applications that have been integrated with iris

    IRS_TB_MA_SISTEMA
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["description_hash"])

    IRIS_HASH = "Jnfo8uhxb1WnqJ8qOrKuyF2ZaWU"
    WEB_HASH = "pHeGrFjQ4lf0UBBXACupX0W5Wdo"
    MOBIL_HASH = "CAuBPQ4pHpZMR04TqOiXBqB-HSQ"
    QUIOSCS_HASH = "mHrrhQUR5aAE3y9MwBJ3ypfzs0k"
    ATE_HASH = "md9zKIG1lJTtVFdve8Gz1X67jrc"
    WEB_DIRECTO_HASH = "pb5eMtmEY4BqSW2zTDr946wAX_w"
    CONSULTES_DIRECTO_HASH = "NEVhba0GhU4PpFa1Ql6T65a8crc"
    ATE_DIRECTO_HASH = "Nam1y0XN7E5Dz65cDTXolIAP0ow"
    PORTAL_HASH = "j1WkdZ_VaGWqHZJO3-AMvt81xlw"

    IRIS_PK = 0
    WEB_PK = 1
    MOBIL_PK = 11
    QUIOSCS_PK = 12
    WEB_DIRECTO = 13
    CONSULTES_DIRECTO = 14
    PORTAL_TRAMITS = 16

    ATE_PK = 100
    ATE_DIRECTO_PK = 101

    description = models.CharField(verbose_name=_("Description"), max_length=20)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    description_hash = models.CharField(verbose_name=_("Description hash"), max_length=100, blank=True)

    def __str__(self):
        return self.description

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.pk is None or not self.description_hash:
            signer = Signer(salt=settings.APPLICATION_HASH_SALT)
            if self.description_es:
                self.description_hash = signer.signature(self.description_es)
            else:
                self.description_hash = signer.signature(self.description)
        super().save(force_insert, force_update, using, update_fields)


class Support(CustomSafeDeleteModel, BasicMaster):
    """
    A support is a tool or media for communicating record cards.

    - 091
    - App

    IRS_TB_MA_SUPORT
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    IRIS = 1
    PHONE = 2
    EMAIL = 3
    LETTER = 4
    RECLAMACIO_INTERNA = 29
    WEB = 10
    COMMUNICATION_MEDIA = 8
    ALTRES_MITJANS = 12

    description = models.CharField(verbose_name=_("Description"), max_length=40)
    order = models.PositiveIntegerField(default=0, db_index=True)
    response_channels = models.ManyToManyField(ResponseChannel, through="iris_masters.ResponseChannelSupport",
                                               blank=True)
    allow_nd = models.BooleanField(verbose_name=_("Allow citizen ND"), default=False)
    communication_media_required = models.BooleanField(verbose_name=_("Requires Communication Media"), default=False)
    register_required = models.BooleanField(verbose_name=_("Requires register code"), default=False)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ("order",)
        unique_together = ("description", "deleted")


class InputChannelSupport(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_CANAL_SUPORT
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["input_channel_id", "support_id"])

    field_error_name = "support"

    input_channel = models.ForeignKey(InputChannel, on_delete=models.CASCADE)
    support = models.ForeignKey(Support, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    user_update_id = UserIdField()

    def __str__(self):
        return "{} - {}".format(self.input_channel.description, self.support.description)

    class Meta:
        ordering = ("order",)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"input_channel": self.input_channel, "support": self.support}


class ApplicantType(CustomSafeDeleteModel, BasicMaster):
    """
    IRS_TB_MA_TIPUS_SOLICITANT
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    CIUTADA = 0
    COLECTIUS = 1
    OPERADOR = 3
    RECLAMACIO_INTERNA = 23

    description = models.CharField(verbose_name=_("Description"), max_length=40)
    order = models.PositiveIntegerField(default=0, db_index=True)
    send_response = models.BooleanField(_("Send Response"), default=True)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ("order",)
        unique_together = ("description", "deleted")

    @staticmethod
    def get_send_response(applicant_type_id):
        try:
            return ApplicantType.objects.get(pk=applicant_type_id).send_response
        except ApplicantType.DoesNotExist:
            return True


class InputChannelApplicantType(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_CANAL_SOLICITANT
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["input_channel_id", "applicant_type_id"])

    field_error_name = "applicant_type"

    input_channel = models.ForeignKey(InputChannel, on_delete=models.CASCADE)
    applicant_type = models.ForeignKey(ApplicantType, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    user_update_id = UserIdField()

    def __str__(self):
        return "{} - {}".format(self.input_channel.description, self.applicant_type.description)

    class Meta:
        ordering = ("order",)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"input_channel": self.input_channel, "applicant_type": self.applicant_type}


class ResponseChannelSupport(CleanEnabledBase, UserTrack):
    objects = iris_cachalot(models.Manager(), extra_fields=["response_channel_id", "support_id"])

    field_error_name = "support"

    response_channel = models.ForeignKey(ResponseChannel, on_delete=models.CASCADE)
    support = models.ForeignKey(Support, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "{} - {}".format(self.response_channel.name, self.support.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"response_channel": self.response_channel, "support": self.support}


class Process(models.Model):
    objects = iris_cachalot(models.Manager(), extra_fields=["id"])

    CLOSED_DIRECTLY = "0"
    DIRECT_EXTERNAL_PROCESSING = "1"
    PLANING_RESOLUTION_RESPONSE = "500"
    RESOLUTION_RESPONSE = "501"
    EVALUATION_RESOLUTION_RESPONSE = "502"
    RESPONSE = "503"
    EXTERNAL_PROCESSING = "504"
    EXTERNAL_PROCESSING_EMAIL = "505"
    RESOLUTION_EXTERNAL_PROCESSING = "506"
    RESOLUTION_EXTERNAL_PROCESSING_EMAIL = "507"

    TYPES = (
        (CLOSED_DIRECTLY, _(u"Closed directly")),
        (DIRECT_EXTERNAL_PROCESSING, _(u"Direct External Processing")),
        (PLANING_RESOLUTION_RESPONSE, _(u"Planning, Resolution, Response")),
        (RESOLUTION_RESPONSE, _(u"Resolution, Response")),
        (EVALUATION_RESOLUTION_RESPONSE, _(u"Evaluation, Resolution, Response")),
        (RESPONSE, _(u"Response")),
        (EXTERNAL_PROCESSING, _(u"External Processing")),
        (EXTERNAL_PROCESSING_EMAIL, _(u"External Processing + Automatic Email")),
        (RESOLUTION_EXTERNAL_PROCESSING, _(u"Resolution, External Processing")),
        (RESOLUTION_EXTERNAL_PROCESSING_EMAIL, _(u"Resolution, External Processing + Automatic Email")),
    )

    id = models.CharField(verbose_name=_(u"ID"), max_length=3, primary_key=True, unique=True, choices=TYPES)
    REQUIRED = {
        EXTERNAL_PROCESSING_EMAIL: ["external_email"],
        RESOLUTION_EXTERNAL_PROCESSING_EMAIL: ["external_email"],
        EXTERNAL_PROCESSING: ["external_service_id"],
        RESOLUTION_EXTERNAL_PROCESSING: ["external_service_id"],
        DIRECT_EXTERNAL_PROCESSING: ["external_service_id"],
    }
    DISABLED_BY_STATE = {
        EXTERNAL_PROCESSING_EMAIL: ["external_service_id"],
        RESOLUTION_EXTERNAL_PROCESSING_EMAIL: [],
        EXTERNAL_PROCESSING: ["external_email"],
        RESOLUTION_EXTERNAL_PROCESSING: ["external_email"],
        DIRECT_EXTERNAL_PROCESSING: ["external_email"],
        CLOSED_DIRECTLY: ["external_email"],
        PLANING_RESOLUTION_RESPONSE: ["external_email"],
        RESOLUTION_RESPONSE: ["external_email"],
        EVALUATION_RESOLUTION_RESPONSE: ["external_email"],
        RESPONSE: ["external_email"],
    }

    def __str__(self):
        return self.get_id_display()

    @property
    def requires(self):
        return self.REQUIRED.get(self.id, [])

    @property
    def disabled(self):
        return self.DISABLED_BY_STATE.get(self.id, [])


class District(models.Model):
    objects = iris_cachalot(models.Manager(), extra_fields=["id", "allow_derivation"])

    CIUTAT_VELLA = 1
    EIXAMPLE = 2
    SANTS_MONTJUIC = 3
    LES_CORTS = 4
    SARRIA_SANTGERVASSI = 5
    GRACIA = 6
    HORTA_GUINARDO = 7
    NOU_BARRIS = 8
    SANT_ANDREU = 9
    SANT_MARTI = 10
    FORA_BCN = 11

    DISTRICTS = (
        (CIUTAT_VELLA, CIUTAT_VELLA),
        (EIXAMPLE, EIXAMPLE),
        (SANTS_MONTJUIC, SANTS_MONTJUIC),
        (LES_CORTS, LES_CORTS),
        (SARRIA_SANTGERVASSI, SARRIA_SANTGERVASSI),
        (GRACIA, GRACIA),
        (HORTA_GUINARDO, HORTA_GUINARDO),
        (NOU_BARRIS, NOU_BARRIS),
        (SANT_ANDREU, SANT_ANDREU),
        (SANT_MARTI, SANT_MARTI),
        (FORA_BCN, FORA_BCN),
    )

    id = models.IntegerField(verbose_name=_(u"ID"), primary_key=True, unique=True, choices=DISTRICTS)
    name = models.CharField(verbose_name=_(u"Name"), max_length=50)
    allow_derivation = models.BooleanField(_("Allow derivation"), default=True)

    def __str__(self):
        return self.name


class ResolutionType(CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_MA_TIPUS_RESOLUCIO
    """
    PROGRAM_ACTION = 3
    objects = iris_cachalot(CustomSafeDeleteManager())

    description = models.CharField(verbose_name=_("Description"), max_length=40)
    can_claim_inside_ans = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=100, db_index=True)

    class Meta:
        ordering = ("order",)
        unique_together = ("description", "deleted")


class ExternalService(models.Model):
    objects = iris_cachalot(models.Manager(), extra_fields=["sender_uuid"])

    sender_uid = models.CharField(max_length=10)
    name = models.CharField(max_length=40)
    active = models.BooleanField(default=True)
    url = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return self.name


class FurniturePickUp(models.Model):
    id = models.IntegerField(verbose_name=_(u"ID"), primary_key=True, unique=True)
    street_code = models.CharField(verbose_name=_(u"Street Code"), max_length=20)
    number = models.CharField(verbose_name=_(u"Number"), max_length=15)
    service_type = models.CharField(verbose_name=_(u"Service type"), max_length=1)
    service_description = models.CharField(verbose_name=_(u"Service description"), max_length=25, blank=True)
    enterprise_name = models.CharField(verbose_name=_(u"Enterprise name"), max_length=40, blank=True)

    def __str__(self):
        return "{} / {}".format(self.street_code, self.number)


class LetterTemplate(UserTrack):
    id = models.IntegerField(verbose_name=_(u"ID"), primary_key=True, unique=True)
    description = models.CharField(verbose_name=_("Description"), max_length=100, unique=True)
    name = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=100, db_index=True)

    def __str__(self):
        return self.description


class DistrictSector(UserTrack):
    """
    Model to register IRIS1 table IRS_TB_MA_DIST_SECT
    """
    dist_sect_id = models.AutoField(primary_key=True)
    description = models.CharField(blank=False, max_length=255)
    flag_ds = models.IntegerField(default=0)
    discharge_date = models.DateTimeField()
    user_id = models.CharField(blank=False, max_length=20)
    fl_authorized = models.IntegerField(default=0)
    list_description = models.CharField(blank=False, max_length=255)
