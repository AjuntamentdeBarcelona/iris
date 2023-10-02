class ThemeMandatoryDrupalFields:
    """
    Class to get the mappong of theme mandatory fields for drupal
    """

    def __init__(self, element_detail) -> None:
        self.element_detail = element_detail
        super().__init__()

    def get_mandatory_fields(self):
        requires_citizen = self.element_detail.requires_citizen
        aggrupation_first = self.element_detail.aggrupation_first
        requires_ubication = self.element_detail.requires_ubication
        return {
            'citizen': {
                'name': requires_citizen,
                'first_surname': requires_citizen,
                'document_type': requires_citizen,
                'document': requires_citizen
            },
            'social_entity': {
                'social_reason': aggrupation_first,
                'cif': aggrupation_first,
                'contact': aggrupation_first
            },
            'ubication': {
                'street_name': requires_ubication,
                'number': requires_ubication,
                'district_ubication': self.element_detail.requires_ubication_district
            }
        }
