from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from record_cards.models import Ubication
from geo_proxy.serializers import UbicationGeoSerializer
from record_cards.serializers import UbicationSerializer
from geo_proxy.utils import geo_json_search, geo_json_reverse


class GeoProxySearchListView(APIView):
    """
    List of Ubication objects from a querystring.
    A list from Nominatim OSM
    locations is displayed.

    If no querystring is specified,
    displays all Ubications in the database.
    """

    @csrf_exempt
    def get(self, request, format=None):
        if request.method == 'GET':
            data = request.GET.copy()
            if not data:
                db_ubications = Ubication.objects.none()
                serializer = UbicationSerializer(db_ubications, many=True)
                return Response(serializer.data)

            # Free-form query
            if 'q' in data:
                ubication_serializer = UbicationGeoSerializer(data=geo_json_search(f"q={data['q']}"), many=True)
                if ubication_serializer.is_valid():
                    return Response(ubication_serializer.data)
                else:
                    db_ubications = Ubication.objects.all()
                    serializer = UbicationSerializer(db_ubications, many=True)
                    return Response(serializer.data)

            # Structured query request
            else:
                parameter_string = '&'.join(f'{param}={param_value}' for param, param_value in data.items())
                ubication_serializer = UbicationGeoSerializer(
                    data=geo_json_search(parameter_string), many=True)
                if ubication_serializer.is_valid():
                    return Response(ubication_serializer.data)
                else:
                    db_ubications = Ubication.objects.all()
                    serializer = UbicationSerializer(db_ubications, many=True)
                    return Response(serializer.data)


class GeoProxyReverseListView(APIView):
    """
    List of Ubication objects given latitude and longitude.
    If any matches are found in the DB
    the API displays the filtered objects.
    If not found, a list from Nominatim OSM
    locations is displayed.

    If no latitude nor longitude are specified,
    displays all Ubications in the database.
    """

    @csrf_exempt
    def get(self, request, format=None):
        if request.method == 'GET':
            data = request.GET.copy()
            # If latitude and longitude are parameters then use reverse
            if 'lat' in data and 'lon' in data:

                # First check if latitude and longitude parameters match any DB entry
                db_ubications = Ubication.objects.filter(latitude=data['lat'], longitude=data['lon'])

                # Return Ubication objects if found inside the DB
                if db_ubications.exists():
                    serializer = UbicationSerializer(db_ubications, many=True)
                    return Response(serializer.data)

                # No results found in DB, we access Nominatim
                else:
                    ubication_serializer = UbicationGeoSerializer(
                        data=geo_json_reverse(f"lat={data['lat']}&lon={data['lon']}"))
                    if ubication_serializer.is_valid():
                        return Response(ubication_serializer.data)
                    else:
                        print(ubication_serializer.errors)
                        db_ubications = Ubication.objects.all()
                        serializer = UbicationSerializer(db_ubications, many=True)
                        return Response(serializer.data)

            # If parameters lat and lon are missing, return current Ubication objects
            else:
                db_ubications = Ubication.objects.all()
                serializer = UbicationSerializer(db_ubications, many=True)
                return Response(serializer.data)
