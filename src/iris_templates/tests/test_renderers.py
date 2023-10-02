import pytest
from mock import Mock

from iris_templates.renderer import DelimitedVarsTemplateRenderer, render_iris_1


class TestDelimitedVarsTemplateRenderer:

    def test_get_headers(self):
        renderer = self.given_an_email_sender()
        headers = renderer.get_header_context("""
        #HEADER1=VALUE1##HEADER2=VALUE"#

        #HEADER3=VALUE3#
        """)
        assert len(headers.keys()) == 3, 'Expected at least 3 vars'
        for i in (1, 3):
            assert headers[f'HEADER{i}'] == f'VALUE{i}', 'Mismatched var with its value'

    def test_get_headers_empty(self):
        renderer = self.given_an_email_sender()
        headers = renderer.get_header_context("")
        assert len(headers.keys()) == 0, 'Expected no headers'

    def test_template_without_vars_should_remove_vars(self):
        renderer = self.given_an_email_sender()
        template = renderer.get_template_without_vars("""
        #HEADER=1#

        A
        """)
        assert template == 'A'

    def given_an_email_sender(self):
        return DelimitedVarsTemplateRenderer(record_card=Mock())


class TestTemplateRenderer:

    @pytest.mark.parametrize('text,expected', (
        ('', ''),
        ('test', 'OK'),
        ('testing', 'testing'),
        ('test ing', 'OK ing'),
        ('test inter test', 'OK inter OK'),
        (
            "<div><p><br></p><p>aquesta va en català, és una prova</p><p><br></p></div>",
            "<div><p></p><p>aquesta va en català, és una prova</p><p></p></div>"
        )
    ))
    def test_var_replacements(self, text, expected):
        assert render_iris_1(text, {'test': 'OK'}) == expected
