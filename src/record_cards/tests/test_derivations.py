import pytest
from django.conf import settings
from mock import patch, Mock
from model_mommy import mommy

from iris_masters.models import District, RecordState
from profiles.tests.utils import create_groups
from record_cards.models import Ubication, RecordCard
from record_cards.record_actions.derivations import (Derivation, DirectDerivation, DistrictDerivation,
                                                     PolygonDerivation, SpatialDerivation, derivate,
                                                     get_derivation_class, DummyDerivation)
from record_cards.tests.utils import CreateRecordCardMixin, CreateDerivationsMixin
from themes.models import DerivationPolygon, Zone, DerivationDistrict
from iris_masters.tests.utils import load_missing_data_districts

@pytest.mark.django_db
class TestDerivations(CreateRecordCardMixin, CreateDerivationsMixin):

    @pytest.mark.parametrize("create_direct_derivation,create_district_derivation,district_id", (
        (True, False, District.CIUTAT_VELLA),
        (False, False, District.CIUTAT_VELLA),
        (False, True, District.CIUTAT_VELLA),
        (False, True, None)
    ))
    def test_derivate_method(self, create_direct_derivation, create_district_derivation, district_id):
        record_card = self.create_record_card(district_id=district_id)
        _, parent, _, _, _, _ = create_groups()
        load_missing_data_districts()
        if create_direct_derivation:
            expected_result = self.create_direct_derivation(element_detail_id=record_card.element_detail_id,
                                                            record_state_id=record_card.record_state_id)
        elif create_district_derivation:
            district_group_id = self.create_district_derivation(element_detail_id=record_card.element_detail_id,
                                                                record_state_id=RecordState.PENDING_VALIDATE)
            expected_result = district_group_id if district_id else None
        else:
            expected_result = None
        assert derivate(record_card, record_card.record_state_id, record_card.ubication.district_id) == expected_result

    @pytest.mark.parametrize("create_direct_derivation,expected_class", (
        (True, DirectDerivation), (False, SpatialDerivation)
    ))
    def test_get_derivation_class(self, create_direct_derivation, expected_class):
        record_card = self.create_record_card()
        if create_direct_derivation:
            self.create_direct_derivation(element_detail_id=record_card.element_detail_id,
                                          record_state_id=record_card.record_state_id)
        assert get_derivation_class(record_card, record_card.record_state_id) is expected_class

    def test_derivation_class(self):
        record_card = self.create_record_card()
        try:
            Derivation(
                record_card, record_card.record_state_id, record_card.ubication.district_id).get_derivation_group()
        except Exception as e:
            assert isinstance(e, NotImplementedError)

    @pytest.mark.parametrize("create_direct_derivation", (True, False))
    def test_direct_derivation_class(self, create_direct_derivation):
        record_card = self.create_record_card()
        if create_direct_derivation:
            expected_result = self.create_direct_derivation(element_detail_id=record_card.element_detail_id,
                                                            record_state_id=record_card.record_state_id)
        else:
            expected_result = None
        assert DirectDerivation(record_card, record_card.record_state_id,
                                record_card.ubication.district_id).get_derivation_group() == expected_result

    @pytest.mark.parametrize("create_district_derivation,district_id,record_state_id,district_state_id", (
        (True, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE),
        (True, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.IN_PLANING),
        (False, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE),
        (True, None, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE),
    ))
    def test_district_derivation_class(self, create_district_derivation, district_id, record_state_id,
                                       district_state_id):
        load_missing_data_districts()
        record_card = self.create_record_card(district_id=district_id, record_state_id=record_state_id)
        if create_district_derivation:
            district_group_id = self.create_district_derivation(element_detail_id=record_card.element_detail_id,
                                                                record_state_id=district_state_id)
            if district_id and record_state_id == district_state_id:
                expected_result = district_group_id
            else:
                expected_result = None
        else:
            expected_result = None
        assert DistrictDerivation(record_card, record_card.record_state_id,
                                  record_card.ubication.district_id).get_derivation_group() == expected_result

    @pytest.mark.parametrize("xetrs89a,yetrs89a", ((2.121, None), (None, 2.333), (None, None)))
    def test_polygon_derivation_ubication_nocoords(self, xetrs89a, yetrs89a):
        load_missing_data_districts()
        ubication = mommy.make(Ubication, user_id="22222", xetrs89a=xetrs89a, yetrs89a=yetrs89a)
        record_card = self.create_record_card(ubication=ubication)
        assert PolygonDerivation(record_card, record_card.record_state_id,
                                 record_card.ubication.district_id).get_derivation_group() is None

    def test_polygon_derivation_no_derivations(self):
        load_missing_data_districts()
        ubication = mommy.make(Ubication, user_id="22222", xetrs89a=2.121, yetrs89a=2.333)
        record_card = self.create_record_card(ubication=ubication)
        assert PolygonDerivation(record_card, record_card.record_state_id,
                                 record_card.ubication.district_id).get_derivation_group() is None

    @pytest.mark.parametrize("return_polygon_code", ("070", PolygonDerivation.all_polygon_code, None))
    def test_polygon_derivation_create_derivations(self, return_polygon_code):
        load_missing_data_districts()
        if not Zone.objects.filter(id=1):
            zone = Zone(id=1)
            zone.save()
        ubication = mommy.make(Ubication, user_id="22222", xetrs89a=2.121, yetrs89a=2.333, street='asdas')
        element_detail = self.create_element_detail()
        dair, parent, _, _, _, _ = create_groups()

        DerivationPolygon.objects.create(polygon_code="070", zone_id=Zone.CARRCENT_PK, group=parent,
                                         record_state_id=RecordState.PENDING_VALIDATE, element_detail=element_detail)
        DerivationPolygon.objects.create(polygon_code=PolygonDerivation.all_polygon_code, zone_id=Zone.CARRCENT_PK,
                                         group=dair, record_state_id=RecordState.PENDING_VALIDATE,
                                         element_detail=element_detail)

        record_card = self.create_record_card(ubication=ubication, element_detail=element_detail)

        mock_polygon_code = Mock(return_value=return_polygon_code)
        with patch("record_cards.record_actions.derivations.PolygonDerivation.get_record_polygon_code",
                   mock_polygon_code):
            derivation_group = PolygonDerivation(record_card, record_card.record_state_id,
                                                 record_card.ubication.district_id).get_derivation_group()
            if return_polygon_code == "070":
                assert derivation_group == parent
            elif return_polygon_code == PolygonDerivation.all_polygon_code:
                assert derivation_group == dair
            else:
                assert derivation_group is None

    @pytest.mark.parametrize("return_polygon_code", ("070", PolygonDerivation.all_polygon_code, None))
    def test_polygon_derivation_getgeobcn_derivations(self, return_polygon_code):
        load_missing_data_districts()
        if not Zone.objects.filter(id=1):
            zone = Zone(id=1)
            zone.save()
        ubication = mommy.make(Ubication, user_id="22222", xetrs89a=2.121, yetrs89a=2.333, street="CARRER")
        element_detail = self.create_element_detail()
        dair, parent, _, _, _, _ = create_groups()

        DerivationPolygon.objects.create(polygon_code="070", zone_id=Zone.CARRCENT_PK, group=parent,
                                         record_state_id=RecordState.PENDING_VALIDATE, element_detail=element_detail)
        DerivationPolygon.objects.create(polygon_code=PolygonDerivation.all_polygon_code, zone_id=Zone.CARRCENT_PK,
                                         group=dair, record_state_id=RecordState.PENDING_VALIDATE,
                                         element_detail=element_detail)

        record_card = self.create_record_card(ubication=ubication, element_detail=element_detail)

        settings.POLYGON_GEO_BCN = True

        mock_polygon_code = Mock(return_value=return_polygon_code)
        with patch("record_cards.record_actions.derivations.PolygonDerivation.get_geo_bcn_polygon_code",
                   mock_polygon_code):
            derivation_group = PolygonDerivation(record_card, record_card.record_state_id,
                                                 record_card.ubication.district_id).get_derivation_group()
            record_card = RecordCard.objects.get(pk=record_card.pk)
            if return_polygon_code:
                assert record_card.ubication.polygon_code
            else:
                assert not record_card.ubication.polygon_code
            if return_polygon_code == "070":
                assert derivation_group == parent
            elif return_polygon_code == PolygonDerivation.all_polygon_code:
                assert derivation_group == dair
            else:
                assert derivation_group is None
        settings.POLYGON_GEO_BCN = False

    def test_dummy_derivation_class(self):
        assert DummyDerivation(return_value=True).get_derivation_group() is True

    @pytest.mark.parametrize("spatial_derivations_returns,expected_return", (
        ([1], 1),
        ([None, 1], 1),
        ([None, None, 1], 1),
        ([None, None, 1, None, 3], 1),
        ([3, None, 1, None, 3], 3),
        ([None, None, None, None], None),
    ))
    def test_spatial_derivation_class(self, spatial_derivations_returns, expected_return):
        spatial_derivations = [DummyDerivation(return_value) for return_value in spatial_derivations_returns]
        assert SpatialDerivation(None, None, None,
                                 spatial_derivations=spatial_derivations).get_derivation_group() == expected_return

    @pytest.mark.parametrize('polygon,district,exception', (
        (True, True, True),
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ))
    def test_spatial_exception(self, polygon, district, exception):
        load_missing_data_districts()
        if not Zone.objects.filter(id=1):
            zone = Zone(id=1)
            zone.save()
        ubication = mommy.make(Ubication, user_id="22222", xetrs89a=2.121, yetrs89a=2.333)
        spatial_derivations = [DummyDerivation(return_value=None, exception=True)]
        element_detail = self.create_element_detail()
        dair, parent, _, _, _, _ = create_groups()
        if polygon:
            DerivationPolygon.objects.create(polygon_code="070", zone_id=Zone.CARRCENT_PK, group=parent,
                                             record_state_id=RecordState.PENDING_VALIDATE,
                                             element_detail=element_detail)
        if district:
            DerivationDistrict.objects.create(district_id=District.CIUTAT_VELLA,
                                              group=dair, record_state_id=RecordState.PENDING_VALIDATE,
                                              element_detail=element_detail)

        record_card = self.create_record_card(ubication=ubication, element_detail=element_detail)
        try:
            with pytest.raises(Exception):
                SpatialDerivation(
                    record_card,
                    RecordState.PENDING_VALIDATE,
                    next_district_id=District.CIUTAT_VELLA,
                    spatial_derivations=spatial_derivations
                ).get_derivation_group()
        except:
            # If exception is not thrown, we need to check if was required
            assert not exception
