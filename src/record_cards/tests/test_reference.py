import pytest
from record_cards.record_actions.normalized_reference import generate_reference, generate_next_reference


class TestReference:

    def test_reference(self):
        valid_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        reference = generate_reference()
        assert type(int(reference[3:])) is int
        for char in reference[:3]:
            assert char in valid_chars

    @pytest.mark.parametrize("record_claimed_reference,expected_reference,expected_num", (
            ('123XLAS', '123XLAS-02', 2),
            ('123XLAS-02', '123XLAS-03', 3),
            ('123XLAS-09', '123XLAS-10', 10),
            ('123XLAS-15', '123XLAS-16', 16),
    ))
    def test_generate_claim_reference(self, record_claimed_reference, expected_reference, expected_num):
        reference, num = generate_next_reference(record_claimed_reference)
        assert reference == expected_reference
        assert num == expected_num
