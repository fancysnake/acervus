"""Tests for the mark name invariants in specs."""

import pytest

from acervus.pacts.mark import InvalidMarkNameError
from acervus.specs.mark import MAX_NAME_LENGTH, clean_mark_name

INVOICE = "invoice"
MIXED_CASE = "Invoice"
PUNCTUATED = "tax-2026_q1"
TWO_WORDS = "two words"


class TestCleanMarkName:
    @staticmethod
    def test_a_plain_name_passes_through() -> None:
        assert clean_mark_name(INVOICE) == INVOICE

    @staticmethod
    def test_it_trims_surrounding_whitespace() -> None:
        assert clean_mark_name(f"  {INVOICE}\n") == INVOICE

    @staticmethod
    def test_case_is_kept() -> None:
        assert clean_mark_name(MIXED_CASE) == MIXED_CASE

    @staticmethod
    def test_punctuation_is_allowed() -> None:
        assert clean_mark_name(PUNCTUATED) == PUNCTUATED

    @staticmethod
    def test_a_name_at_the_limit_passes() -> None:
        longest = "m" * MAX_NAME_LENGTH

        assert clean_mark_name(longest) == longest

    @staticmethod
    @pytest.mark.parametrize("name", ("", "   ", "\t\n"))
    def test_a_blank_name_raises(*, name) -> None:
        with pytest.raises(InvalidMarkNameError):
            clean_mark_name(name)

    @staticmethod
    def test_an_overlong_name_raises() -> None:
        with pytest.raises(InvalidMarkNameError):
            clean_mark_name("m" * (MAX_NAME_LENGTH + 1))

    @staticmethod
    @pytest.mark.parametrize("name", (TWO_WORDS, "tab\there", "line\nbreak"))
    def test_inner_whitespace_raises(*, name) -> None:
        with pytest.raises(InvalidMarkNameError):
            clean_mark_name(name)

    @staticmethod
    @pytest.mark.parametrize("name", ("docs:invoice", "one,two"))
    def test_a_reserved_character_raises(*, name) -> None:
        with pytest.raises(InvalidMarkNameError):
            clean_mark_name(name)

    @staticmethod
    def test_the_message_names_the_offender() -> None:
        with pytest.raises(InvalidMarkNameError, match=TWO_WORDS):
            clean_mark_name(TWO_WORDS)
