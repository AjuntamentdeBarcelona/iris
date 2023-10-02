class ExcelBaseStyles:

    def get_column_header(self):
        header_styles = {
            'height': 15,
            'style': {
                'fill': {'fill_type': 'solid', 'start_color': 'c0c0c0'},
                'font': {'bold': True, 'color': "000000"},
                'alignment': {'horizontal': 'center'},
                'border_side': {'border_style': 'thin', 'color': '000000'},
            },
            'column_width': self.set_columns_width()
        }
        return header_styles

    body = {
        'height': 15,
        'style': {
            'fill': {'fill_type': 'solid', 'start_color': 'FFFFFF'},
            'font': {'color': "000000"},
            'border_side': {'border_style': 'thin', 'color': '000000'},
            'alignment': {'horizontal': 'general', 'wrap_text': False},
        }
    }

    def set_columns_width(self):
        return 50
