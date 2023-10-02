import pytest

from ariadna.serializers import AriadnaSerializer


@pytest.mark.django_db
class TestAriadnaSerializer:

    @pytest.mark.parametrize("year,input_number,used,valid", (
            (None, 97485454, True, False),
            (2000, None, True, False),
            (2000, 97485454, None, False),
    ))
    def test_ariadna_serializer(self, year, input_number, used, valid):
        data = {
            "year": year,
            "input_number": input_number,
            "input_office": "aaaaaaaaaa",
            "destination_office": "aaaaaaaaaa",
            "presentation_date": "2019-07-11",
            "applicant_type": "aaaaaaaaaa",
            "applicant_surnames": "aaaaaaaaaaaaa",
            "applicant_name": "test test",
            "applicant_doc": "aaaaaaaaaa",
            "matter_type": "aaaaaaaaaa",
            "issue": "aaaaaaaaaa",
            "used": used,
            "date_us": "2019-07-11T11:50:54+02:00"
        }
        ser = AriadnaSerializer(data=data)
        assert ser.is_valid() is valid
