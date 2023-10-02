from copy import deepcopy

from django.db import transaction


class ElementDetailCopy:

    def __init__(self, previous_detail) -> None:
        super().__init__()
        self.previous_detail = previous_detail
        self.element_detail = None

    def copy(self, user_id, new_fields) -> object:
        """
        Create a copy of the indicated element detail and, changing the translated descriptions and copying
         the related objects too

        :param user_id: identifier of the user that dies the copy
        :param new_fields: dict with new fields
               {"description_ca": "", "description_es": "", "description_en": "", "element_id"}
        :return:
        """
        with transaction.atomic():
            self.element_detail = deepcopy(self.previous_detail)
            self.element_detail.pk = None
            self.element_detail.user_id = user_id
            self._copy_new_fields(new_fields)
            self.element_detail.save()

            self._copy_detail_relations()
            return self.element_detail

    def _copy_new_fields(self, new_fields) -> None:
        """
        Copy new descriptions to element detail

        :param new_fields: dict with new languages descriptions
               {"description_ca": "", "description_es": "", "description_en": "",}
        :return:
        """
        for field, value in new_fields.items():
            setattr(self.element_detail, field, value)

    def _copy_detail_relations(self) -> None:
        """
        Copy all detail related objects to the new one

        :return:
        """
        # keywords Keyword
        self._copy_related_objects("keyword_set", "detail")
        # direct derivations DerivationDirect
        self._copy_related_objects("derivationdirect_set", "element_detail")
        # district derivations DerivationDistrict
        self._copy_related_objects("derivationdistrict_set", "element_detail")
        # ElementDetailGroup
        self._copy_related_objects("elementdetailgroup_set", "element_detail")
        # features - ElementDetailFeature
        self._copy_related_objects("feature_configs", "element_detail")
        # response_channels - ElementDetailResponseChannel
        self._copy_related_objects("elementdetailresponsechannel_set", "elementdetail")
        # groups - ElementDetailThemeGroup
        self._copy_related_objects("elementdetailthemegroup_set", "element_detail")
        # applications - ApplicationElementDetail
        self._copy_related_objects("applicationelementdetail_set", "detail")
        # group_profiles - GroupProfileElementDetail
        self._copy_related_objects("groupprofileelementdetail_set", "element_detail")

    def _copy_related_objects(self, detail_relation, detail_field) -> None:
        for related_object in getattr(self.previous_detail, detail_relation).all():
            related_object.pk = None
            setattr(related_object, detail_field, self.element_detail)
            related_object.save()
