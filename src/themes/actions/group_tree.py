from django.db.models import Q

from iris_masters.models import RecordState
from themes.models import ElementDetailGroup, ElementDetail


class GroupThemeTree:
    """
    Class responsible for obtaining and building the theme tree for a given group. The theme tree for a group depends
    on the Group configuration (tree visibility setting and hierarchy), ElementDetail (derivations) and the district.

    The relation between groups and themes is simplified by the ElementDetailGroup model, that tracks the themes that
    belong to a Group or groups and which are their parents.

    Example:

        - Medi Ambient Coordinator (Medi Ambient shares all its descendant groups themes)
        ---- Enllumenat (All the enllumenat groups share its themes, but no the Medi Ambient themes)
        ---- Voreres (All the Voreres groups share its themes, but no the Medi Ambient themes)

    The district filter is important for themes based on ubication, since the ubications define the district and which
    group is the owner/responsible of solving it.
    """

    def __init__(self, group):
        self.group = group

    @property
    def ambit_group(self):
        """
        Group for filtering the tree. If the group has configured to see their direct ascendant or any superior
        instance. For example, an Operador can be configured for viewing its Responsable or its Coordinador themes.
        :return:  Group plate for filtering the tree.
        """
        if self.group.is_root_node():
            return self.group

        if not self.group.tree_levels:
            return self.group
        # On MPTT tree group.level indicates the depth of the node, being 0 the root.
        tree_level = max(self.group.level - self.group.tree_levels, 0)
        return self.group.get_ancestors().get(level=tree_level)

    def is_group_record(self, record):
        """
        Check if the group can resolve a record or must perform a change to one of its themes.
        :param record: Record card being worked
        :return: True if the group can resolve the record
        """
        if not record.element_detail.allow_resolution_change:
            return True
        is_valid = self.themes_for_record(record, element_detail_id=record.element_detail_id).exists()
        if not is_valid:
            # If not ambit record, we must check if the owner group allows others to resolve (validate_thematic_tree)
            district = record.ubication.district if record.ubication and record.ubication.district else None
            owner = self.theme_group_owner(record.element_detail, district)
            return not owner or not owner.validate_thematic_tree  # Valid if not requires theme tree validation
        return True

    def theme_group_owner(self, element_detail, district=None):
        """
        The theme's owner is the one of the first derivation (RecordState.PENDING_VALIDATE) filtering by district
        (District Derivations) or not. The owner group defines the way of using their themes.

        :param element_detail: Element detail for getting the owner
        :param district: Filter by district
        :return: Group owner for the element detail and district.
        """
        if district:
            d = element_detail.derivationdistrict_set.filter(
                record_state_id=RecordState.PENDING_VALIDATE, district_id=district, enabled=True,
            ).first()
            if d:
                return d.group
        d = element_detail.derivationdirect_set.filter(
            record_state_id=RecordState.PENDING_VALIDATE, enabled=True
        ).first()
        return d.group if d else None

    def must_validate_thematic_tree(self, record):
        """
        The record will require a theme change if the current theme belongs to a group with validate thematic tree.
        :param record:
        :return: True if the theme must be changed before the group can resolve it
        """
        return

    def themes_for_record(self, record, **kwargs):
        """
        :param record:
        :return: Valid themes for the group and the record.
        """
        district = record.ubication.district if record.ubication and record.ubication.district else None
        return self.themes_for_district(district, **kwargs)

    def themes_for_district(self, district=None, **kwargs):
        qs = self.get_group_themes_for_district(district, **kwargs)
        return ElementDetail.objects.filter(id__in=qs.values_list("element_detail_id", flat=True))

    def get_group_themes_for_district(self, district=None, **kwargs):
        """
        :param district:
        :return:
        """
        qs = self.get_group_theme_qs(**kwargs)
        if district:
            qs = qs.filter(Q(district=district) | Q(district__isnull=True))
        return qs

    def get_group_theme_qs(self, **kwargs):
        """
        :return: All the related ElementDetailGroup for the group and its descendants.
        """
        return ElementDetailGroup.objects.filter(
            group=self.ambit_group, **kwargs
        ).select_related('element_detail')
