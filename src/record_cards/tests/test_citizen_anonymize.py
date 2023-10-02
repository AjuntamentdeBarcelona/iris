import pytest
from model_mommy import mommy

from record_cards.anonymize.citizen_anonymize import CitizenAnonymize
from record_cards.models import Citizen


@pytest.mark.django_db
class TestCitizenAnonymize:

    def test_anonymize_char_fields(self):
        citizen = mommy.make(Citizen, user_id="22222")
        CitizenAnonymize(citizen)._anonymize_char_fields()
        for char_field in CitizenAnonymize.ANONYM_CHAR_FIELDS:
            assert getattr(citizen, char_field) == CitizenAnonymize.ANONYM_CHAR_KEY

    def test_anonymize(self):
        citizen = mommy.make(Citizen, user_id="22222")
        CitizenAnonymize(citizen).anonymize()
        assert citizen.dni == str(citizen.pk)
        assert citizen.doc_type == Citizen.PASS
        assert citizen.sex == Citizen.UNKNOWN
        assert citizen.mib_code is None
        assert citizen.birth_year is None
