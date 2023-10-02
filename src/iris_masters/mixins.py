from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class CleanUniqueActiveBase:
    field_error_name = None
    validation_error_message = _("Active previous register exists")

    def clean(self):
        super().clean()
        if self.is_active():
            self.clean_active()

    def is_active(self):
        """
        :return: True if instance is active else False
        """
        raise NotImplementedError("Define the is active condition")

    def clean_active(self):
        """
        Check if there is another active object
        :return:
        """
        filter_fields = self.get_initial_filter_fields()
        filter_fields.update(self.get_extra_filter_fields())
        if self.__class__.objects.filter(**filter_fields).exclude(pk=self.pk):
            raise ValidationError({self.get_field_error_name(): self.get_validation_error_message()})

    def get_initial_filter_fields(self):
        """
        :return: Dict with initial filter fields
        """
        raise NotImplementedError

    def get_field_error_name(self):
        """
        :return: Return field error name if it's declared
        """
        if not self.field_error_name:
            raise Exception("Field error name not defined")
        return self.field_error_name

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        raise NotImplementedError

    def get_validation_error_message(self):
        """
        :return: str
        """
        return self.validation_error_message


class CleanEnabledBase(CleanUniqueActiveBase):

    validation_error_message = _("Enabled previous register exists")

    def is_active(self):
        """
        :return: True if instance is active else False
        """
        return self.enabled

    def get_initial_filter_fields(self):
        """
        :return: Dict with initial filter fields
        """
        return {"enabled": True}


class CleanSafeDeleteBase(CleanUniqueActiveBase):

    def is_active(self):
        """
        :return: True if instance is active else False
        """
        return not self.deleted

    def get_initial_filter_fields(self):
        """
        :return: Dict with initial filter fields
        """
        return {"deleted__isnull": True}
