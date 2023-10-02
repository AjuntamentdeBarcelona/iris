import pytest
from geo_proxy.utils import check_display_name, check_duplicates, translate_type_search, translate_type_reverse
from geo_proxy.serializers import UbicationGeoSerializer
from geo_proxy.tests.utils import CreateJsonResponseMixin


class TestUtils(CreateJsonResponseMixin):

    @pytest.mark.parametrize("language,street_types_boolean",
                             (("GL", True),
                              ("GL", False),
                              ("CA", True),
                              ("CA", False),
                              ("ES", True),
                              ("ES", False)))
    def test_translate_type_search(self, language, street_types_boolean):
        json_req = self.create_search_json(language)
        json_req_copy = self.create_search_json(language)
        if street_types_boolean:
            street_types = self.create_street_type_list(language)
        else:
            street_types = None
        translate_type_search(json_req, street_types=street_types)
        if street_types_boolean:
            for i in range(len(json_req)):
                assert "type" in json_req[i]
                if "road" not in json_req_copy[i]["address"]:
                    assert "road" in json_req[i]["address"]
        else:
            assert json_req == json_req_copy

    @pytest.mark.parametrize("language", ("GL", "CA", "ES"))
    def test_check_duplicates(self, language):
        json_req = self.create_search_json(language)
        translate_type_search(json_req, street_types=self.create_street_type_list(language))
        assert len(check_duplicates(json_req)) == 1

    @pytest.mark.parametrize("language,long_name",
                             (("GL", True),
                              ("GL", False),
                              ("CA", True),
                              ("CA", False),
                              ("ES", True),
                              ("ES", False)))
    def test_check_display_name(self, language, long_name):
        max_len = 120
        if long_name:
            json_req = self.create_long_json(language)
        else:
            json_req = self.create_simple_json(language)
        check_display_name(json_req, max_len=max_len)
        assert len(json_req['display_name']) <= max_len

    @pytest.mark.parametrize("language,street_types_boolean",
                             (("GL", True),
                              ("GL", False),
                              ("CA", True),
                              ("CA", False),
                              ("ES", True),
                              ("ES", False)))
    def test_translate_type_reverse(self, language, street_types_boolean):
        json_req = self.create_simple_json(language)
        json_req_copy = self.create_simple_json(language)
        if street_types_boolean:
            street_types = self.create_street_type_list(language)
        else:
            street_types = None
        translate_type_reverse(json_req, street_types=street_types)
        if street_types_boolean:
            assert "type" in json_req
            if "road" not in json_req_copy["address"]:
                assert "road" in json_req["address"]
        else:
            assert json_req == json_req_copy


class TestUbicationGeoSerializer(CreateJsonResponseMixin):

    def test_search_serializer(self):
        data = self.create_ready_json_search()
        ser = UbicationGeoSerializer(data=data, many=True)
        assert ser.is_valid()

    @pytest.mark.parametrize("lat, lon",
                             ((10.3443211, 9.99541123),
                              (12.432132, -2.5431167),
                              (20.432111, 40.321111985),
                              (42.7743718, -9.057560197197557)))
    def test_reverse_serializer(self, lat, lon):
        data = self.create_ready_json_reverse(lat=lat, lon=lon)
        ser = UbicationGeoSerializer(data=data)
        assert ser.is_valid()
