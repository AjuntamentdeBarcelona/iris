from rest_framework import serializers
from record_cards.models import Ubication


class AddressGeoSerializer(serializers.Serializer):
    """
    Address serializer that takes into account Nominatim naming conventions in jsonv2
    """
    road = serializers.CharField(default='street')
    neighbourhood = serializers.CharField(default='')
    city_district = serializers.CharField(default='')
    house_number = serializers.CharField(default='')
    city = serializers.CharField(default='')
    postcode = serializers.CharField(default='')

    class Meta:
        model = Ubication
        fields = (
            'road',
            'neighbourhood',
            'city_district',
            'house_number',
            'city',
            'postcode',
        )


class UbicationGeoSerializer(serializers.ModelSerializer):
    """
    Ubication serializer that takes into account Nominatim naming conventions in jsonv2
    """

    # Nominatim Fields
    category = serializers.CharField()
    display_name = serializers.CharField()
    lat = serializers.CharField()
    lon = serializers.CharField()
    type = serializers.CharField()

    # Ubication fields
    via_type = serializers.SerializerMethodField('get_and_trans_via_type')
    street = serializers.SerializerMethodField('get_address_road')
    street2 = serializers.SerializerMethodField('get_address_house_number')
    official_street_name = serializers.SerializerMethodField('get_display_name')
    neighborhood = serializers.SerializerMethodField('get_address_neighbourhood')
    district = serializers.SerializerMethodField('get_address_city_district')
    latitude = serializers.SerializerMethodField('get_lat')
    longitude = serializers.SerializerMethodField('get_lon')
    address = AddressGeoSerializer()

    class Meta:
        model = Ubication
        fields = (
            'id',
            'via_type',
            'street',
            'street2',
            'official_street_name',
            'neighborhood',
            'district',
            'latitude',
            'longitude',
            'address',
            'category',
            'display_name',
            'lat',
            'lon',
            'type',
        )

    def get_and_trans_via_type(self, obj):
        if obj['type']:
            return obj['type']
        else:
            return ''

    def get_display_name(self, obj):
        return obj['display_name']

    def get_address_road(self, obj):
        return obj['address']['road']

    def get_address_house_number(self, obj):
        return obj['address']['house_number']

    def get_address_neighbourhood(self, obj):
        return obj['address']['neighbourhood']

    def get_address_city_district(self, obj):
        return obj['address']['city_district']

    def get_lat(self, obj):
        return obj['lat']

    def get_lon(self, obj):
        return obj['lon']
