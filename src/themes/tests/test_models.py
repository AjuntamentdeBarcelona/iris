import pytest
from model_mommy import mommy
from safedelete import HARD_DELETE

from iris_masters.models import District
from profiles.models import Group
from profiles.tests.utils import create_groups
from themes.models import ElementDetailGroup, GroupProfileElementDetail, Area, Element, ElementDetail
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestAreaModel:

    def test_first_area(self):
        ElementDetail.objects.all().delete(force_policy=HARD_DELETE)
        Element.objects.all().delete(force_policy=HARD_DELETE)
        Area.objects.all().delete(force_policy=HARD_DELETE)
        assert Area().set_code() == '01'

    def test_area_code(self):
        Area.objects.create(description='AAA', area_code='01')
        Area.objects.create(description='AAA', area_code='05')
        Area.objects.create(description='AAA', area_code='06')
        assert Area().set_code() == '07'


@pytest.mark.django_db
class TestElementModel:

    def test_first_element_code(self):
        self.when_other_area_with_element_exists()
        area = Area.objects.create(description='AAA', area_code='01')
        assert Element(area=area).set_code() == '0100'

    def test_element_code(self):
        self.when_other_area_with_element_exists()
        area = Area.objects.create(description='AAA', area_code='01')
        Element.objects.create(area=area, description='BBB', element_code='0100')
        Element.objects.create(area=area, description='BBB', element_code='0191')
        assert Element(area=area).set_code() == '0192'

    def when_other_area_with_element_exists(self):
        area = Area.objects.create(description='AAA', area_code='02')
        Element.objects.create(area=area, description='AAAA', element_code='0201')


@pytest.mark.django_db
class TestElementDetailModel(CreateThemesMixin):

    def test_get_ambit_for_direct_derivation_with_dair(self):
        load_missing_data()
        load_missing_data_process()
        element_detail = self.create_element_detail(create_direct_derivations=True,create_district_derivations=False)
        dair = self.when_all_derivations_are_for_root_group(element_detail)
        theme_ambit = self.when_theme_ambits_are_got(element_detail, 'derivationdirect_set')
        assert len(theme_ambit) == 1
        assert theme_ambit[0].get('group_id') == dair.id

    def test_get_ambit_for_districts_with_root(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail(create_direct_derivations=False, create_district_derivations=True)
        dair = self.when_all_derivations_are_for_root_group(element_detail)
        theme_ambit = self.when_theme_ambits_are_got(element_detail, 'derivationdistrict_set')
        self.should_return_ambits_per_district_and_group_in_hierarchy(theme_ambit, dair)

    def test_get_ambit_for_districts_with_children_group(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail(create_direct_derivations=False, create_district_derivations=True)
        group = self.when_all_derivations_are_for_root_grand_son(element_detail)
        theme_ambit = self.when_theme_ambits_are_got(element_detail, 'derivationdistrict_set')
        self.should_return_ambits_per_district_and_group_in_hierarchy(theme_ambit, group)

    def test_register_theme_ambit_district(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail(create_direct_derivations=False,
                                                    create_district_derivations=True)
        group = self.when_all_derivations_are_for_root_grand_son(element_detail)
        element_detail.register_theme_ambit()
        self.should_register_ambit_for_district_for_whole_hierarchy(element_detail, group)

    def test_register_theme_ambit_direct(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail(create_direct_derivations=True,
                                                    create_district_derivations=False)
        group = self.when_all_derivations_are_for_root_grand_son(element_detail)
        element_detail.register_theme_ambit()
        self.should_register_ambit_for_direct_for_whole_hierarchy(element_detail, group)

    @pytest.mark.parametrize("create_group_assignation", (True, False))
    def test_has_group_profiles(self, create_group_assignation):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail()
        if create_group_assignation:
            group = mommy.make(Group, user_id="22", profile_ctrl_user_id="222")
            GroupProfileElementDetail.objects.create(group=group, element_detail=element_detail)
        assert element_detail.has_group_profiles == create_group_assignation

    def test_group_can_see_own(self):
        load_missing_data()
        load_missing_data_process()
        dair, parent, _, _, _, _ = create_groups()
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        assert element_detail.group_can_see(parent.group_plate) is True

    def test_group_can_see_ancestor(self):
        load_missing_data()
        load_missing_data_process()
        dair, parent, _, _, _, _ = create_groups()
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        assert element_detail.group_can_see(dair.group_plate) is True

    def test_group_can_see_descendant(self):
        load_missing_data()
        load_missing_data_process()
        dair, parent, soon, _, _, _ = create_groups()
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        assert element_detail.group_can_see(soon.group_plate) is False

    def test_group_can_see_other_ambit(self):
        load_missing_data()
        load_missing_data_process()
        _, parent, _, _, noambit, _ = create_groups()
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        assert element_detail.group_can_see(noambit.group_plate) is False

    def test_first_element_code(self):
        load_missing_data()
        load_missing_data_process()
        self.when_other_element_with_detail_exists()
        area = Area.objects.create(description='AAA', area_code='01')
        element = Element.objects.create(area=area, description='BBB', element_code='0124')
        assert ElementDetail(element=element).set_code() == '012400'

    def test_element_code(self):
        load_missing_data()
        load_missing_data_process()
        self.when_other_element_with_detail_exists()
        area = Area.objects.create(description='AAA', area_code='01')
        element = Element.objects.create(area=area, description='BBB', element_code='0190')
        ElementDetail.objects.create(element=element, description='BBB', detail_code='019000')
        ElementDetail.objects.create(element=element, description='BBB', detail_code='019091')
        assert ElementDetail(element=element).set_code() == '019092'

    def when_other_element_with_detail_exists(self):
        area = Area.objects.create(description='AAA', area_code='02')
        element = Element.objects.create(area=area, description='AAAA', element_code='0201')
        ElementDetail.objects.create(element=element, description='AAAA', detail_code='020101')

    def when_all_derivations_are_for_root_group(self, element_detail):
        dair = Group.objects.root_nodes().first()
        element_detail.derivationdistrict_set.update(group=dair)
        element_detail.derivationdirect_set.update(group=dair)
        return dair

    def when_all_derivations_are_for_root_grand_son(self, element_detail):
        group = Group.objects.filter(level=2).first()
        element_detail.derivationdistrict_set.update(group=group)
        element_detail.derivationdirect_set.update(group=group)
        return group

    def when_theme_ambits_are_got(self, element_detail, derivation_type):
        theme_ambit = []
        element_detail.get_ambit_from_derivation(theme_ambit, derivation_type)
        return theme_ambit

    def should_return_ambit_per_district(self, theme_ambits):
        district_ambits = {a.get('district_id'): a for a in theme_ambits}
        missing = [
            district_id for district_id, _ in District.DISTRICTS
            if district_id not in district_ambits and district_id != District.FORA_BCN and district_id is not None
        ]
        assert not missing, f'Should include one ambit per district, missing {missing}'

    def should_return_ambits_per_district_and_group_in_hierarchy(self, theme_ambits, group):
        for group_ambit in group.get_ancestors(include_self=True):
            ambits = [a for a in theme_ambits if a.get('group_id') == group_ambit.id]
            self.should_return_ambit_per_district(ambits)

    def should_register_ambit_for_direct_for_whole_hierarchy(self, element_detail, group):
        themes = ElementDetailGroup.objects.filter(element_detail=element_detail).values('group_id', 'district_id')
        hierarchy = list(group.get_ancestors(include_self=True))
        per_group = {a.get('group_id'): a for a in themes}
        missing = [g for g in hierarchy if g.id not in per_group]
        assert not missing, f'Missing direct derivation ambits for groups {missing}'

    def should_register_ambit_for_district_for_whole_hierarchy(self, element_detail, group):
        themes = ElementDetailGroup.objects.filter(element_detail=element_detail).values('group_id', 'district_id')
        self.should_return_ambits_per_district_and_group_in_hierarchy(themes, group)
