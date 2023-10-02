from iris_masters.models import Parameter
from record_cards.models import Citizen, Applicant


def create_default_applicant(sender, **kwargs):
    dni = Parameter.get_parameter_by_key("AGRUPACIO_PER_DEFECTE", "INTERN")
    citizen, _ = Citizen.objects.get_or_create(dni=dni, defaults={
        'blocked': False,
        'doc_type': Citizen.PASS,
        'response': False,
        'name': 'Ayuntamiento',
        'first_surname': 'Interno',
        'second_surname': '-',
    })
    Applicant.objects.get_or_create(citizen=citizen)
