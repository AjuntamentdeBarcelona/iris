import pytest

from record_cards.record_actions.get_recode_from_text import get_record_code_from_text


class TestGetRecordCodeFromText:

    @pytest.mark.parametrize("text,expected_code", (
            ("Codi de la fitxa duplicada: I09345848L-01", "I09345848L-01"),
            ("Codi de la fitxa duplicada: 3598CPS3598CPS", "3598CPS"),
            ("Codi de la fitxa duplicada: 4381BZC", "4381BZC"),
            ("Codi de la fitxa duplicada: 039AUIB", "039AUIB"),
            ("Codi de la fitxa duplicada: AAA1234", "AAA1234"),
            ("Codi de la fitxa duplicada: AAA1234-02", "AAA1234-02"),
            ("Codi de la fitxa duplicada: 4381BZC-02", "4381BZC-02"),
            ("Codi de la fitxa duplicada: 039AUIB-02", "039AUIB-02"),
            ("Codi de la fitxa duplicada:", "")
    ))
    def test_review_answer_action(self, text, expected_code):
        assert get_record_code_from_text(text) == expected_code
