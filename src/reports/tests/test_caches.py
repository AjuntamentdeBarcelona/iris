import pytest
from model_mommy import mommy

from features.models import ValuesType, Values, Feature
from reports.caches import FeaturesCache, ValuesCache


@pytest.mark.django_db
class TestFeaturesCache:
    @property
    def features(self):
        values_type = mommy.make(ValuesType, user_id="222")
        features = []
        for index in range(5):
            if index % 2 == 0:
                feature = mommy.make(Feature, user_id="222")
            else:
                feature = mommy.make(Feature, user_id="222", values_type=values_type)
            features.append(feature)
        return features

    def test_load_cache_data(self):
        features = self.features
        features_cache = FeaturesCache()

        for feature in features:
            assert feature.pk in features_cache.features
            assert feature.description == features_cache.features[feature.pk]["description"]
            if feature.values_type_id:
                assert feature.values_type_id == features_cache.features[feature.pk]["values_type_id"]
            else:
                assert features_cache.features[feature.pk]["values_type_id"] is None

    def test_get_feature_description(self):
        features = self.features
        features_cache = FeaturesCache()

        for feature in features:
            assert feature.description == features_cache.get_feature_description(feature.pk)

    def test_get_values_type_id(self):
        features = self.features
        features_cache = FeaturesCache()

        for feature in features:
            assert feature.values_type_id == features_cache.get_values_type_id(feature.pk)


@pytest.mark.django_db
class TestValuesCache:

    @property
    def values(self):
        values_type = mommy.make(ValuesType, user_id="222")
        return [mommy.make(Values, user_id="222", values_type=values_type) for _ in range(5)]

    def test_load_cache_data(self):
        values = self.values
        values_cache = ValuesCache()

        for value in values:
            assert value.pk in values_cache.items
            assert value.description == values_cache.items[value.pk]["description"]

    def test_get_value_description(self):
        values = self.values
        values_cache = ValuesCache()

        for value in values:
            assert value.description == values_cache.get_item_description(value.pk)
