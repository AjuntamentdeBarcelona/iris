from features.models import Feature, Values
from iris_masters.models import RecordState, RecordType, InputChannel, ApplicantType, Support
from main.caches import DescriptionCache


class FeaturesCache:

    def __init__(self) -> None:
        self.features = {}
        self.load_data()

    def load_data(self):
        for feature in Feature.objects.only("description", "values_type_id"):
            if feature.pk not in self.features:
                self.features[feature.pk] = {
                    "description": feature.description,
                    "values_type_id": feature.values_type_id
                }

    def _get_feature(self, feature_id):
        return self.features.get(feature_id)

    def get_feature_description(self, feature_id):
        feature = self._get_feature(feature_id)
        return feature["description"] if feature else ""

    def get_values_type_id(self, feature_id):
        feature = self._get_feature(feature_id)
        return feature["values_type_id"] if feature else None


class ValuesCache(DescriptionCache):

    def get_queryset(self):
        return Values.objects.all()


class RecordStateCache(DescriptionCache):

    def get_queryset(self):
        return RecordState.objects.filter(enabled=True)


class RecordTypeCache(DescriptionCache):

    def get_queryset(self):
        return RecordType.objects.all()


class InputChannelCache(DescriptionCache):

    def get_queryset(self):
        return InputChannel.objects.all()


class ApplicantTypeCache(DescriptionCache):

    def get_queryset(self):
        return ApplicantType.objects.all()


class SupportCache(DescriptionCache):

    def get_queryset(self):
        return Support.objects.all()


class QuequicomCache:

    def __init__(self) -> None:
        super().__init__()
        self.features_cache = FeaturesCache()
        self.values_cache = ValuesCache()
        self.record_state_cache = RecordStateCache()
        self.record_type_cache = RecordTypeCache()
        self.input_channel_cache = InputChannelCache()
        self.applicant_type_cache = ApplicantTypeCache()
        self.support_cache = SupportCache()
