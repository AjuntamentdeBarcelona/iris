from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from drf_chunked_upload.models import ChunkedUpload

from custom_safedelete.managers import CustomSafeDeleteManager
from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.models import UserTrack
from main.cachalot_decorator import iris_cachalot
from record_cards.managers import RecordFileManager
from record_cards.models import ChunkedUploadMixin


def support_info_path(instance, filename):
    now = timezone.now()
    return "support_files/{}/{}/{}/{}".format(now.year, now.month, now.day, filename)


class SupportInfo(CustomSafeDeleteModel, UserTrack):

    objects = iris_cachalot(CustomSafeDeleteManager(), extra_fields=["type"])

    FAQS = 0
    GLOSSARY = 1
    DOCUMENTATION = 2
    VIDEO = 3
    NEWS = 4

    TYPES = (
        (FAQS, _("Frequently Asked Questions")),
        (GLOSSARY, _("Glossary")),
        (DOCUMENTATION, _("Documentation")),
        (VIDEO, _("Video")),
        (NEWS, _("News")),
    )

    TRAINING_COURSES = 0
    DAIQ_REPORTS = 1
    USER_MANUALS = 2
    REGULATIONS = 3
    LINKS = 4
    OTHERS = 5

    CATEGORIES = (
        (TRAINING_COURSES, _("Self Training Courses")),
        (DAIQ_REPORTS, _("General statistical DAIQ reports")),
        (USER_MANUALS, _("User Manuals")),
        (REGULATIONS, _("Regulations")),
        (LINKS, _("Links")),
        (OTHERS, _("Others"))
    )

    title = models.CharField(_("Title"), max_length=200, db_index=True)
    description = models.TextField(_("Description"))
    type = models.IntegerField(_("Type"), choices=TYPES, db_index=True)
    category = models.IntegerField(_("Category"), choices=CATEGORIES, null=True, blank=True,
                                   help_text=_("Category for Documentation Type"))
    file = models.FileField(_("File"), blank=True, null=True, upload_to=support_info_path)
    link = models.URLField(_("Link"), blank=True,
                           help_text=_("Youtube link for Video Type or link for Document Type"))

    class Meta:
        ordering = ("type", "title")

    def __str__(self):
        return self.title


class SupportChunkedFile(ChunkedUploadMixin, ChunkedUpload):
    objects = RecordFileManager()

    support_info = models.ForeignKey(SupportInfo, verbose_name=_("Support Info"), on_delete=models.CASCADE,
                                     db_index=True)
    user = models.ForeignKey(get_user_model(), related_name="%(class)s", on_delete=models.CASCADE)

    class Meta:
        ordering = ("-completed_at", "-status", "-created_at",)

    def __str__(self):
        return "{} - file {}".format(self.support_info.title, self.pk)
