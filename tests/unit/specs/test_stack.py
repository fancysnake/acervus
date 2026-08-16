"""Tests for the stack name invariants in specs."""

import pytest

from acervus.pacts.stack import InvalidStackNameError
from acervus.specs.stack import MAX_NAME_LENGTH, clean_stack_name

TRIP = "iceland trip"
MIXED_CASE = "Iceland Trip"
SPACE = " "


class TestCleanStackName:
    @staticmethod
    def test_a_plain_name_passes_through() -> None:
        assert clean_stack_name(TRIP) == TRIP

    @staticmethod
    def test_spaces_are_allowed() -> None:
        assert SPACE in clean_stack_name(TRIP)

    @staticmethod
    def test_it_trims_the_ends() -> None:
        assert clean_stack_name(f"  {TRIP}\n") == TRIP

    @staticmethod
    def test_it_collapses_runs_of_whitespace() -> None:
        assert clean_stack_name("iceland   trip") == TRIP

    @staticmethod
    def test_a_tab_counts_as_a_space() -> None:
        assert clean_stack_name("iceland\ttrip") == TRIP

    @staticmethod
    def test_case_is_kept() -> None:
        assert clean_stack_name(MIXED_CASE) == MIXED_CASE

    @staticmethod
    def test_a_name_at_the_limit_passes() -> None:
        longest = "s" * MAX_NAME_LENGTH

        assert clean_stack_name(longest) == longest

    @staticmethod
    @pytest.mark.parametrize("name", ("", "   ", "\t\n"))
    def test_a_blank_name_raises(*, name) -> None:
        with pytest.raises(InvalidStackNameError):
            clean_stack_name(name)

    @staticmethod
    def test_an_overlong_name_raises() -> None:
        with pytest.raises(InvalidStackNameError):
            clean_stack_name("s" * (MAX_NAME_LENGTH + 1))
