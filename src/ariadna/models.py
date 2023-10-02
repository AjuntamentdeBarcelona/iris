from django.db import models
from django.utils.translation import ugettext_lazy as _
from iris_masters.models import UserTrack
from iris_masters.mixins import CleanSafeDeleteBase
from custom_safedelete.models import CustomSafeDeleteModel


class Ariadna(UserTrack, CleanSafeDeleteBase, CustomSafeDeleteModel):
    """
    IRS_TB_REGISTRE
    """
    NIF = 0
    NIE = 1
    PASS = 2
    field_error_name = "code"

    DOC_TYPES = (
        (NIF, _("NIF")),
        (NIE, _("NIE")),
        (PASS, _("PASS"))
    )
    year = models.IntegerField(verbose_name=_("Year"))
    input_number = models.IntegerField(verbose_name=_("Input number"))
    input_office = models.CharField(verbose_name=_("Input office"), max_length=10)
    destination_office = models.CharField(verbose_name=_("Destination office"), max_length=10)
    presentation_date = models.DateField(verbose_name=_("Presentation date"))
    matter_type = models.CharField(verbose_name=_("Matter type"), max_length=10)
    issue = models.CharField(verbose_name=_("Issue"), max_length=200)
    # todo: mark flag when assigning the record
    used = models.BooleanField(verbose_name=_("Used"), default=False)
    date_us = models.DateTimeField(verbose_name=_("Date us"))
    code = models.CharField(max_length=12)
    applicant_type = models.CharField(verbose_name=_("Applicant type"), max_length=10)
    applicant_name = models.CharField(verbose_name=_("Applicant name"), max_length=15, blank=True, null=True)
    applicant_surnames = models.CharField(verbose_name=_("Applicant surnames"), max_length=30, blank=True, null=True)
    applicant_doc_type = models.PositiveSmallIntegerField(_(u"Document Type"), default=NIF, choices=DOC_TYPES,
                                                          blank=True, null=True)
    applicant_doc = models.CharField(verbose_name=_("Applicant doc"), max_length=10, blank=True, null=True)

    social_reason = models.CharField(verbose_name=_("social_reason"), max_length=60, blank=True, null=True)
    contact = models.CharField(verbose_name=_("contact"), max_length=10, blank=True, default="Ariadna", null=True)

    class Meta:
        unique_together = ("year", "input_number", "deleted")

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.pk:
            self.code = "{}/{}".format(self.year, str(self.input_number).zfill(6))
        super().save(force_insert=force_insert, force_update=force_update, using=using,
                     update_fields=update_fields)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {}


class AriadnaRecord(models.Model):
    record_card = models.ForeignKey("record_cards.RecordCard", on_delete=models.CASCADE, related_name="registers")
    code = models.CharField(max_length=12)
