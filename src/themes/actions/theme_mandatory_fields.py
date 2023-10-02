class ThemeMandatoryFields:
    """
    Class to get the mapping of themes mandatory fields
    """
    mandatory_maps = {
        0: {'requires_citizen': False, 'requires_ubication': False, 'requires_ubication_district': False,
            'aggrupation_first': False},
        1: {'requires_citizen': True, 'requires_ubication': False, 'requires_ubication_district': False,
            'aggrupation_first': False},
        2: {'requires_citizen': False, 'requires_ubication': True, 'requires_ubication_district': False,
            'aggrupation_first': False},
        3: {'requires_citizen': True, 'requires_ubication': True, 'requires_ubication_district': False,
            'aggrupation_first': False},
        4: {'requires_citizen': True, 'requires_ubication': False, 'requires_ubication_district': False,
            'aggrupation_first': True},
        5: {'requires_citizen': True, 'requires_ubication': True, 'requires_ubication_district': False,
            'aggrupation_first': True},
        6: {'requires_citizen': False, 'requires_ubication': False, 'requires_ubication_district': True,
            'aggrupation_first': False},
        7: {'requires_citizen': True, 'requires_ubication': False, 'requires_ubication_district': True,
            'aggrupation_first': False},
        8: {'requires_citizen': True, 'requires_ubication': False, 'requires_ubication_district': True,
            'aggrupation_first': True},
        9: {'requires_citizen': False, 'requires_ubication': True, 'requires_ubication_district': True,
            'aggrupation_first': False},
        10: {'requires_citizen': True, 'requires_ubication': True, 'requires_ubication_district': True,
             'aggrupation_first': False},
        11: {'requires_citizen': True, 'requires_ubication': True, 'requires_ubication_district': True,
             'aggrupation_first': True},
    }

    def __init__(self, element_detail) -> None:
        self.element_detail = element_detail
        super().__init__()

    def get_element_detail_map(self) -> dict:
        """
        Get the map mandatory of a element detail

        :return: Dict map of element detail
        """
        return {
            'requires_citizen': self.element_detail.requires_citizen,
            'requires_ubication': self.element_detail.requires_ubication,
            'requires_ubication_district': self.element_detail.requires_ubication_district,
            'aggrupation_first': self.element_detail.aggrupation_first
        }

    def get_mapping_value(self) -> int or None:
        """
        Looks for the maping key of the mandatory maps of an element detail

        :return: Maping  key of the mandatory map or None if it's not found
        """
        element_detail_map = self.get_element_detail_map()
        for key, mandatory_map in self.mandatory_maps.items():
            if mandatory_map == element_detail_map:
                return key
        return None
