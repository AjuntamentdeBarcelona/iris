from django.db import models
from django.utils.translation import ugettext_lazy as _

from custom_safedelete.managers import CustomSafeDeleteManager
from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.models import UserTrack
from main.cachalot_decorator import iris_cachalot
from themes.models import ElementDetail


class Protocols(CustomSafeDeleteModel, UserTrack):
    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["protocol_id"])

    protocol_id = models.CharField(verbose_name=_("Protocol id"), max_length=30)
    description = models.TextField(verbose_name=_("Description"))
    short_description = models.TextField(verbose_name=_("Short description"), default=" ")

    def __str__(self):
        return self.protocol_id

    class Meta:
        unique_together = ("protocol_id", "deleted")

    @property
    def can_be_deleted(self):
        return not ElementDetail.objects.filter(external_protocol_id=self.protocol_id).exists()
