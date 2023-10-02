import pytest

from record_cards.record_actions.update_fields import RecordDictUpdateFields, UpdateComment
from record_cards.tests.utils import CreateRecordCardMixin, FeaturesMixin


@pytest.mark.django_db
class TestRecordDictUpdateFields(FeaturesMixin, CreateRecordCardMixin):

    def test_record_related_object_to_dict(self):
        record_card = self.create_record_card(create_record_card_response=True)
        ubication_dict = RecordDictUpdateFields.record_related_object_to_dict(record_card.ubication)
        for pop_key in ["created_at", "updated_at", "_state"]:
            assert pop_key not in ubication_dict

    def test_record_update_fields(self):
        features = self.create_features()
        special_features = self.create_features(is_special=True)
        record_card = self.create_record_card(create_record_card_response=True, features=features,
                                              special_features=special_features)
        record_dict = RecordDictUpdateFields(record_card).record_update_fields()
        for key in ["description", "mayorship", "features", "special_features", "ubication", "recordcardresponse"]:
            assert key in record_dict

        self.assert_features(record_dict["features"])
        self.assert_features(record_dict["special_features"])

    @staticmethod
    def assert_features(features):
        for feature in features:
            for key in ["feature_id", "feature", "value"]:
                assert key in feature


@pytest.mark.django_db
class TestUpdateComment(FeaturesMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize("update_record", (False, True))
    def test_record_values_changed(self, update_record):
        record_card = self.create_record_card(create_record_card_response=True)
        initial_dict = RecordDictUpdateFields(record_card).record_update_fields()
        if update_record:
            record_card.mayorship = not record_card.mayorship
            record_card.save()
        update_dict = RecordDictUpdateFields(record_card).record_update_fields()
        assert UpdateComment(initial_dict, update_dict).record_values_changed is update_record

    @pytest.mark.parametrize("update_record", (False, True))
    def test_get_update_comment(self, update_record):
        record_card = self.create_record_card(create_record_card_response=True)
        initial_dict = RecordDictUpdateFields(record_card).record_update_fields()
        if update_record:
            record_card.mayorship = not record_card.mayorship
            record_card.save()
        update_dict = RecordDictUpdateFields(record_card).record_update_fields()
        comment = UpdateComment(initial_dict, update_dict).get_update_comment()
        if update_record:
            assert comment
        else:
            assert comment == ""
