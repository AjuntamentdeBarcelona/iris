from django.utils.translation import ugettext_lazy as _

from features.models import Values
from iris_masters.models import ResponseChannel


class RecordDictUpdateFields:
    """

    """

    def __init__(self, record_card) -> None:
        super().__init__()
        self.record_card = record_card

    def record_update_fields(self):
        return {
            "description": self.record_card.description,
            "mayorship": self.record_card.mayorship,
            "features": self.set_features("recordcardfeatures_set"),
            "special_features": self.set_features("recordcardspecialfeatures_set"),
            "ubication": self.record_related_object_to_dict(self.record_card.ubication),
            "recordcardresponse": self.record_related_object_to_dict(
                self.record_card.recordcardresponse) if hasattr(self.record_card, "recordcardresponse") else {}
        }

    def set_features(self, relation):
        return [self.get_feature_dict(record_feature)
                for record_feature in getattr(self.record_card, relation).filter(enabled=True).order_by("feature_id")]

    @staticmethod
    def get_feature_dict(record_feature):
        feature_dict = {"feature_id": record_feature.feature_id, "feature": record_feature.feature.description,
                        "value": record_feature.value}

        if record_feature.feature.values_type:
            try:
                feature_dict["value_description"] = Values.objects.get(pk=int(record_feature.value)).description \
                    if record_feature.value else ""
            except (Values.DoesNotExist, ValueError):
                feature_dict["value_description"] = ""

        return feature_dict

    @staticmethod
    def record_related_object_to_dict(related_object):
        if not related_object:
            return {}
        related_object_dict = related_object.__dict__.copy()
        related_object_dict.pop("updated_at", None)
        related_object_dict.pop("created_at", None)
        related_object_dict.pop("_state", None)
        return related_object_dict


class UpdateComment:
    """
    Create the update comment from a copy of the initial state and one from the update instance
    """

    def __init__(self, initial_record, updated_record) -> None:
        super().__init__()
        self.initial_record = initial_record
        self.updated_record = updated_record

    def get_update_comment(self) -> str:
        """

        :return:
        """
        comment = ""
        if self.record_values_changed:
            comment = self.set_description_comment(self.initial_record["description"],
                                                   self.updated_record["description"], comment)
            comment = self.set_mayorship_comment(self.initial_record["mayorship"], self.updated_record["mayorship"],
                                                 comment)
            comment = self.set_features_comment(self.initial_record["features"], self.updated_record["features"],
                                                comment, False)
            comment = self.set_features_comment(self.initial_record["special_features"],
                                                self.updated_record["special_features"],
                                                comment, True)
            comment = self.set_response_comment(self.initial_record["recordcardresponse"],
                                                self.updated_record["recordcardresponse"], comment)
            comment = self.set_ubication_comment(self.initial_record["ubication"], self.updated_record["ubication"],
                                                 comment)

        return comment

    @staticmethod
    def set_description_comment(initial_description, updated_description, comment):
        if initial_description != updated_description:
            comment += _("RecordCard description was updated. Previous description was: {}.").format(
                initial_description) + "\n"
        return comment

    @staticmethod
    def set_mayorship_comment(initial_mayorship, updated_mayorship, comment):
        if initial_mayorship != updated_mayorship:
            if initial_mayorship:
                flag_text = _("It was mark before the update")
            else:
                flag_text = _("It was unmark before the update")
            comment += _("RecordCard mayorship flag was updated. {}.").format(flag_text) + "\n"
        return comment

    @staticmethod
    def set_features_comment(initial_features, udpated_features, comment, special_features=False):
        if initial_features != udpated_features:
            if initial_features:
                features_text = ""
                for feature in initial_features:
                    value = feature["value_description"] if "value_description" in feature else feature["value"]

                    features_text += "{} = {}, ".format(feature["feature"], value)

            else:
                features_text = _("There were no previous features.")

            if special_features:
                initial_text = _("RecordCard special features have been changed. Previous special features are")
            else:
                initial_text = _("RecordCard features have been changed. Previous features are")

            comment += "{}: {}.".format(initial_text, features_text) + "\n"
        return comment

    @staticmethod
    def set_response_comment(initial_response, updated_response, comment):
        if initial_response != updated_response:
            if not initial_response:
                comment += _("RecordCard has not previous response") + "\n"
            else:
                response_channel_name = ResponseChannel.objects.get(pk=initial_response["response_channel_id"]).name
                comment += _("RecordCard response was updated. Previous response has to be sent to {} by {}.").format(
                    initial_response["address_mobile_email"], response_channel_name) + "\n"
        return comment

    @staticmethod
    def set_ubication_comment(initial_ubication, updated_ubication, comment):
        if initial_ubication != updated_ubication:
            if not initial_ubication:
                comment += _("RecordCard has not previous ubication") + "\n"
            else:
                comment += _("RecordCard ubication was updated. Previous ubication was: {} {} {} {}.").format(
                    initial_ubication["via_type"], initial_ubication["street"], initial_ubication["street2"],
                    initial_ubication["neighborhood"]) + "\n"
        return comment

    @property
    def record_values_changed(self) -> bool:
        """
        Check if record values have changed
        """
        return self.initial_record != self.updated_record
