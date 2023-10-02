from django.db import models
from django.utils.translation import gettext_lazy as _

from custom_safedelete.managers import CustomSafeDeleteManager
from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.models import UserTrack
from iris_masters.mixins import CleanSafeDeleteBase
from main.cachalot_decorator import iris_cachalot


class ValuesType(CleanSafeDeleteBase, CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_MA_LLISTA_VALORS
    """
    objects = iris_cachalot(CustomSafeDeleteManager())
    field_error_name = "description"

    description = models.CharField(verbose_name=_("Description"), max_length=100)

    class Meta:
        unique_together = ("description", "deleted")
        ordering = ("description", )

    def __str__(self):
        return self.description

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"description": self.description}


class Values(CleanSafeDeleteBase, CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_MA_VALORS_LLISTA
    """
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["values_type"])
    field_error_name = "description"

    values_type = models.ForeignKey(ValuesType, on_delete=models.PROTECT)
    description = models.CharField(verbose_name=_("Description"), max_length=100)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        unique_together = ("description", "values_type", "deleted")
        ordering = ("order", )

    def __str__(self):
        return self.description

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"description": self.description, "values_type": self.values_type}


class Mask(models.Model):
    """
    IRS_TB_MA_CARACTERISTICA_MASK

    * Taula no trobada a IRISXAL
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["id"])

    ANY_CHAR = 1
    ONLY_LETTERS = 2
    ANY_NUMBER = 3
    INTEGER = 4
    PHONE_NUMBER = 5
    POSTAL_CODE = 6
    DATE_FORMAT = 7
    HOUR_FORMAT = 8

    MASKS = (
        (ANY_CHAR, _(u"Any Character")),
        (ONLY_LETTERS, _(u"Only Letters")),
        (ANY_NUMBER, _(u"Any Number")),
        (INTEGER, _(u"Integer")),
        (PHONE_NUMBER, _(u"Phone Number (9 digits)")),
        (POSTAL_CODE, _(u"Postal Code (5 digits)")),
        (DATE_FORMAT, _(u"Date Format DD/MM/YYYY")),
        (HOUR_FORMAT, _(u"Hour Format HH:MM")),
    )

    TEXT = "Text"
    NUMBER = "Number"
    DATE = "Date"
    TIME = "Time"

    TYPES = (
        (TEXT, TEXT),
        (NUMBER, NUMBER),
        (DATE, DATE),
        (TIME, TIME),
    )

    id = models.IntegerField(verbose_name=_(u"ID"), primary_key=True, unique=True, choices=MASKS)
    description = models.CharField(verbose_name=_(u"Description"), max_length=15)
    type = models.CharField(verbose_name=_(u"Type"), max_length=15, choices=TYPES, default=NUMBER)

    def __str__(self):
        return self.get_id_display()


class Feature(CleanSafeDeleteBase, CustomSafeDeleteModel, UserTrack):
    """
    IRS_TB_MA_ATRIBUTS
    """
    objects = iris_cachalot(CustomSafeDeleteManager())
    field_error_name = "description"

    description = models.CharField(verbose_name=_("Description"), max_length=100)
    values_type = models.ForeignKey(ValuesType, null=True, blank=True, on_delete=models.PROTECT)
    is_special = models.BooleanField(_(u"Special"), default=False)
    mask = models.ForeignKey(Mask, on_delete=models.PROTECT, null=True, blank=True)
    explanatory_text = models.TextField(_(u"Explanatory Text"), blank=True)
    codename = models.CharField(max_length=40, blank=True, default='', help_text=_(u"GET parameter for integrations"))
    codename_iris = models.CharField(max_length=40, blank=True, default='', null=True,
                                     help_text=_(u"GET parameter for backoffice GET integration"))
    visible_for_citizen = models.BooleanField(
        default=True,
        help_text=_("This feature won't be show to citizens, only in backoffice.")
    )
    editable_for_citizen = models.BooleanField(default=True,
                                               help_text=_("This feature will be filled with automatic values."))

    class Meta:
        unique_together = ("description", "values_type", "deleted")
        ordering = ("description", )

    def __str__(self):
        return self.description

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"description": self.description, "values_type": self.values_type}
