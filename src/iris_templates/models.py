from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from custom_safedelete.managers import CustomSafeDeleteManager
from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.mixins import CleanEnabledBase, CleanSafeDeleteBase
from iris_masters.models import BasicMaster, ResponseType, RecordType, UserTrack
from iris_templates.managers import IrisTemplateRecordTypesManager
from main.cachalot_decorator import iris_cachalot
from profiles.models import Group


class IrisTemplate(CleanSafeDeleteBase, CustomSafeDeleteModel, BasicMaster):
    """
    Iris template model
    """
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["group"])

    field_error_name = "description"

    response_type = models.ForeignKey(ResponseType, null=True, blank=True, on_delete=models.PROTECT)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    record_types = models.ManyToManyField(RecordType, through='iris_templates.IrisTemplateRecordTypes')
    write_medium_catalan = models.TextField(_("Write Medium (CA)"), blank=True,
                                            help_text=_("Template for write mediums in catalan"))
    write_medium_spanish = models.TextField(_("Write Medium (ES)"), blank=True,
                                            help_text=_("Template for write mediums in spanish"))
    write_medium_english = models.TextField(_("Write Medium (EN)"), blank=True,
                                            help_text=_("Template for write mediums in spanish"))
    sms_medium_catalan = models.TextField(_("SMS Medium (CA)"), blank=True,
                                          help_text=_("Template for SMS mediums in catalan"))
    sms_medium_spanish = models.TextField(_("SMS Medium (ES)"), blank=True,
                                          help_text=_("Template for SMS mediums in spanish"))
    sms_medium_english = models.TextField(_("SMS Medium (EN)"), blank=True,
                                          help_text=_("Template for SMS mediums in spanish"))

    def __str__(self):
        return "{} - {}".format(self.description, self.response_type.description)

    def clean(self):
        super().clean()
        validation_errors = {}
        self.check_language_field(self.write_medium_catalan, self.write_medium_spanish, 'write_medium_catalan',
                                  'write_medium_spanish', validation_errors)
        self.check_language_field(self.write_medium_spanish, self.write_medium_catalan, 'write_medium_spanish',
                                  'write_medium_catalan', validation_errors)
        self.check_language_field(self.sms_medium_catalan, self.sms_medium_spanish, 'sms_medium_catalan',
                                  'sms_medium_spanish', validation_errors)
        self.check_language_field(self.sms_medium_spanish, self.sms_medium_catalan, 'sms_medium_spanish',
                                  'sms_medium_catalan', validation_errors)
        if validation_errors:
            raise ValidationError(validation_errors)

    @property
    def is_group_template(self):
        return self.group is not None

    @staticmethod
    def check_language_field(base_field_value, check_field_value, base_field_label, check_field_label,
                             validation_errors):
        """
        If one language field is filled and the other no, add a validation error.

        :param base_field_value: value of the base field to check
        :param check_field_value: value of the check field to check
        :param base_field_label: name of the base field to check
        :param check_field_label: name of the check field to check
        :param validation_errors: Dictionary with validation errors
        :return:
        """
        if base_field_value and not check_field_value:
            validation_errors.update({check_field_label: _("If {} is filled, {} must be filled to").format(
                base_field_label, check_field_label)})

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            'description': self.description
        }


class IrisTemplateRecordTypes(CleanEnabledBase, UserTrack):
    """
    Record Types related to an Iris Template
    """
    objects = iris_cachalot(IrisTemplateRecordTypesManager(), extra_fields=["iris_template_id", "record_type_id"])
    field_error_name = "record_type"

    iris_template = models.ForeignKey(IrisTemplate, on_delete=models.CASCADE)
    record_type = models.ForeignKey(RecordType, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_('Enabled'), default=True, db_index=True)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {
            'iris_template': self.iris_template,
            'record_type': self.record_type
        }

    def clean(self):
        super().clean()
        validation_errors = {}
        self.check_unique_response_type_for_record_type(
            self.record_type.pk, self.iris_template.response_type_id, self.iris_template.pk, validation_errors)
        if validation_errors:
            raise ValidationError(validation_errors)

    @staticmethod
    def check_unique_response_type_for_record_type(record_type_pk, response_type_pk, iris_template_pk,
                                                   validation_errors):
        """

        :param record_type_pk:
        :param response_type_pk:
        :param iris_template_pk:
        :param validation_errors: Dictionary with validation errors
        :return:
        """
        if not IrisTemplateRecordTypes.objects.unique_response_type_for_record_type(
                record_type_pk, response_type_pk, iris_template_pk):
            validation_errors.update(
                {'record_type': _("There are another template with the same ResponseType for this RecordType")})
