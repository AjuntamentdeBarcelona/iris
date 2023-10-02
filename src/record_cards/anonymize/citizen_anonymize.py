
class CitizenAnonymize:
    ANONYM_CHAR_KEY = "XxxxX"
    ANONYM_CHAR_FIELDS = ["name", "first_surname", "second_surname", "full_normalized_name", "normalized_first_surname",
                          "normalized_second_surname"]

    def __init__(self, citizen) -> None:
        super().__init__()
        self.citizen = citizen

    def anonymize(self):
        self._anonymize_char_fields()
        self.citizen.dni = str(self.citizen.pk)
        self.citizen.doc_type = self.citizen.PASS
        self.citizen.birth_year = None
        self.citizen.sex = self.citizen.UNKNOWN
        self.citizen.mib_code = None
        self.citizen.save()

    def _anonymize_char_fields(self):
        for char_field in self.ANONYM_CHAR_FIELDS:
            setattr(self.citizen, char_field, self.ANONYM_CHAR_KEY)
