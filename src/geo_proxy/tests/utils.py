class CreateJsonResponseMixin:

    CAT = 'CA'
    GAL = 'GL'

    def create_street_type_list(self, lang_code):
        if lang_code == self.GAL:
            return [
                "Avenida",
                "Rúa",
                "Gran Vía",
                "Parque"
            ]
        elif lang_code == self.CAT:
            return [
                "Avinguda",
                "Carrer",
                "Gran Via",
                "Parc"
            ]
        else:
            return [
                "Avenida",
                "Calle",
                "Gran Vía",
                "Parque"
            ]

    def create_simple_json(self, lang_code=None):
        if lang_code == self.CAT:
            return {
                'lat': '41.024321',
                'lon': '2.2213432',
                'display_name': 'Test català amb road',
                'address': {
                    'test': 'Parc de prova',
                }
            }
        elif lang_code == self.GAL:
            return {
                'lat': '41.024321',
                'lon': '2.2213432',
                'display_name': 'Test galego con road',
                'address': {
                    'road': 'Gran Vía de proba',
                    'house_number': '12'
                }
            }
        else:
            return {
                'lat': '41.024321',
                'lon': '2.2213432',
                'display_name': 'Test castellano con road',
                'address': {
                    'road': 'Test de prueba',
                }
            }

    def create_long_json(self, lang_code=None):
        if lang_code == self.CAT:
            return {
                'lat': '41.024321',
                'lon': '2.2213432',
                'display_name': 'Test català llarg' * 5,
                'address': {
                    'road': 'Parc de prova',
                }
            }
        elif lang_code == self.GAL:
            return {
                'lat': '41.024321',
                'lon': '2.2213432',
                'display_name': 'Test galego con road' * 5,
                'address': {
                    'road': 'Gran Vía de proba',
                    'house_number': '12'
                }
            }
        else:
            return {
                'lat': '41.024321',
                'lon': '2.2213432',
                'display_name': 'Test castellano con road' * 5,
                'address': {
                    'road': 'Parque de prueba',
                }
            }

    def create_search_json(self, lang_code=None):
        if lang_code == self.CAT:
            return [
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test català amb road',
                    'address': {
                        'road': 'Parc de prova',
                    }
                },
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test català sense road',
                    'address': {
                        'test': 'Carrer de prova',
                    }
                },
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test català amb road sense tipus',
                    'address': {
                        'road': 'Test de prova',
                        'house_number': '12'
                    }
                }
            ]
        elif lang_code == self.GAL:
            return [
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test galego con road',
                    'address': {
                        'road': 'Gran Vía de proba',
                        'house_number': '12'
                    }
                },
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test galego sen road',
                    'address': {
                        'test': 'Rúa de proba',
                    }
                },
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test galego con road sen tipo',
                    'address': {
                        'road': 'Test de proba',
                    }
                }
            ]
        else:
            return [
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test castellano con road',
                    'address': {
                        'road': 'Parque de prueba',
                    }
                },
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test castellano sin road',
                    'address': {
                        'test': 'Avenida de prueba',
                        'house_number': '12'
                    }
                },
                {
                    'lat': '41.024321',
                    'lon': '2.2213432',
                    'display_name': 'Test castellano con road sin tipo',
                    'address': {
                        'road': 'Test de prueba',
                    }
                }
            ]

    def create_ready_json_search(self):
        return [
            {
                'lat': '41.383384649999996',
                'lon': '2.1750998298342505',
                'display_name': 'Plaça de Sant Felip Neri, el Gòtic, Ciutat Vella, Barcelona, Barcelonès, Barcelona, '
                                'Catalunya, 08001, España',
                'category': 'highway',
                'type': 'Plaça',
                'address': {
                    'road': 'Plaça de Sant Felip Neri',
                    'neighbourhood': 'el Gòtic',
                    'suburb': 'Ciutat Vella',
                    'city': 'Barcelona',
                    'county': 'Barcelonès',
                    'state_district': 'Barcelona',
                    'state': 'Catalunya',
                    'postcode': '08001',
                    'country': 'España',
                    'country_code': 'es'
                }
            }
        ]

    def create_ready_json_reverse(self, lat, lon):
        return {
            'lat': f'{lat}', 'lon': f'{lon}',
            'category': 'highway',
            'type': 'Calle',
            'addresstype': 'road',
            'name': None,
            'display_name': 'Tirwun, Bauchi, Nigeria',
            'address': {
                'city_district': 'Tirwun',
                'city': 'Bauchi',
                'state': 'Bauchi',
                'country': 'Nigeria',
                'country_code': 'ng',
                'road': 'Tirwun'}
        }
