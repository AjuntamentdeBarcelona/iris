from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from iris_masters.models import ExternalService, UserIdField
from record_cards.models import RecordCard


class ExternalRecordId(models.Model):
    external_code = models.CharField(max_length=60)
    record_card = models.ForeignKey(RecordCard, on_delete=models.PROTECT, related_name='external_ids')
    service = models.ForeignKey(ExternalService, on_delete=models.PROTECT)


def opendata_path(instance, filename):
    now = timezone.now()
    return "opendata/{}/{}/{}/{}".format(now.year, now.month, now.day, filename)


class BatchFile(models.Model):
    CREATED = 1
    IN_VALIDATION = 2
    VALIDATED = 3

    STATUSES = (
        ("CREATED", CREATED),
        ("IN_VALIDATION", IN_VALIDATION),
        ("VALIDATED", VALIDATED),
    )

    process = models.CharField(max_length=4, db_index=True)
    validated_by = UserIdField(blank=True, default='')
    validated_at = models.DateTimeField(null=True)
    file = models.FileField(verbose_name=_("Record File"), upload_to=opendata_path, max_length=250,
                            null=True, blank=True)
    status = models.IntegerField(choices=STATUSES, default=CREATED)
    sent_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    oldest_date_limit = models.DateTimeField(_("Oldest date limit"), null=True, blank=True)
    newest_date_limit = models.DateTimeField(_("Newest date limit"), null=True, blank=True)
    trimestre = models.IntegerField(_("Trimestre"), choices=[(1, 1), (2, 2), (3, 3), (4, 4)], null=True, blank=True)
    year = models.IntegerField(_("Year"), validators=[MinValueValidator(2000)], null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    @classmethod
    def create_for_now(cls, process):
        return cls.objects.create(
            process=process,
            file=opendata_path(None, timezone.now().isoformat() + '.csv')
        )

    def validate(self, user_id):
        self.status = BatchFile.IN_VALIDATION
        self.validated_at = timezone.now()
        self.validated_by = user_id
        self.save()


class BiirisFilesExtractionDetail(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    record_card = models.ForeignKey(RecordCard, on_delete=models.PROTECT)
    special_feature = models.CharField(max_length=100, blank=True)
    file_assigned = models.IntegerField(null=True, blank=True)
    file_name = models.CharField(max_length=102, blank=True)
    register_code = models.CharField(max_length=12, blank=True)
    resolution_user = models.CharField(max_length=20, blank=True)
    special_feature_id = models.CharField(max_length=60, blank=True)
    reasigned_days = models.CharField(max_length=10, blank=True)
    response_operator = models.CharField(max_length=10, blank=True)
    claimed = models.BooleanField(default=False)
    claimed_date = models.DateField(blank=True)
    reasignation_response_operator = models.BooleanField(default=False)
    files_fill = models.CharField(max_length=13, blank=True)
    claimed_response_profile = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class GpoIndicators(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    indicator = models.CharField(max_length=40, blank=True)
    description = models.CharField(max_length=100, blank=True)
    historic = models.BooleanField(default=False)
    order = models.IntegerField(default=0)


class GpoHistoric(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    indicator = models.CharField(max_length=40, blank=True)
    month = models.CharField(max_length=2, blank=True)
    year = models.CharField(max_length=4, blank=True)
    value = models.CharField(max_length=20, blank=True)


class GpoSect(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    district_sector_id = models.IntegerField()
    identifier = models.CharField(max_length=4, blank=True)


class OpenDataModel(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    normalized_record_id = models.CharField(max_length=100, null=True)
    type = models.CharField(max_length=100, null=True)
    area = models.CharField(max_length=100, null=True)
    element = models.CharField(max_length=100, null=True)
    detail = models.CharField(max_length=100, null=True)
    created_day = models.CharField(max_length=100, null=True)
    created_month = models.CharField(max_length=100, null=True)
    created_year = models.CharField(max_length=100, null=True)
    closing_day = models.CharField(max_length=100, null=True)
    closing_month = models.CharField(max_length=100, null=True)
    closing_year = models.CharField(max_length=100, null=True)
    district_id = models.CharField(max_length=100, null=True)
    district = models.CharField(max_length=100, null=True)
    neighborhood_id = models.CharField(max_length=100, null=True)
    neighborhood = models.CharField(max_length=100, null=True)
    research_zone = models.CharField(max_length=100, null=True)
    via_type = models.CharField(max_length=100, null=True)
    street = models.CharField(max_length=100, null=True)
    street2 = models.CharField(max_length=100, null=True)
    xetrs89a = models.CharField(max_length=100, null=True)
    yetrs89a = models.CharField(max_length=100, null=True)
    longitude = models.CharField(max_length=100, null=True)
    latitude = models.CharField(max_length=100, null=True)
    support = models.CharField(max_length=100, null=True)
    response_channel = models.CharField(max_length=100)
    validated = models.BooleanField(default=False)


class BiView(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    record_response_data = models.IntegerField()
    response_channel_id = models.IntegerField()
    reason_id = models.IntegerField()
    reason_desc = models.CharField(max_length=100)
    record_type_id = models.IntegerField()
    element_detail_id = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closing_date = models.DateTimeField()
    record_state_id = models.IntegerField()
    support_id = models.IntegerField()
    id_applicant_type = models.IntegerField()
    id_applicant = models.IntegerField()
    id_citizen = models.IntegerField()
    id_social = models.IntegerField()
    id_ubication = models.IntegerField()
    id_district = models.IntegerField()
    barri_name = models.CharField(max_length=100)
    calle = models.CharField(max_length=100)
    tipus_via = models.CharField(max_length=100)
    numero = models.CharField(max_length=100)
    barri_id = models.IntegerField()
    special_feature_value = models.CharField(max_length=100)
    first_reas_date = models.DateTimeField()
    reas_id = models.IntegerField()
    first_result_group = models.IntegerField()
    second_result_group = models.IntegerField()
    research_zone = models.CharField(max_length=100)
    statistical_sector = models.CharField(max_length=100)
    response_channel_id = models.IntegerField()
    ans_limit_date = models.DateTimeField()
    responsible_profile_id = models.IntegerField()
    user_id = models.CharField(max_length=100)
    input_channel_id = models.IntegerField()
    record_state_id = models.IntegerField()
    geocode_district_id = models.IntegerField()
    coordinate_x = models.IntegerField()
    coordinate_y = models.IntegerField()
    record_parent_claimed = models.CharField(max_length=100)
    normalized_record_id = models.CharField(max_length=100)
    claims_number = models.IntegerField()

    class Meta:
        db_table = 'bi_aux'
        managed = False
