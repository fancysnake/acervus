"""Tests for the stack noun contracts in pacts."""

import dataclasses
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from acervus.pacts.stack import (
    InvalidStackNameError,
    StackDTO,
    StackNotFoundError,
    StackSummary,
)

TRIP = "iceland trip"
TAXES = "taxes 2026"


class TestStackDTO:
    @staticmethod
    def test_valid() -> None:
        stack = StackDTO(id=1, name=TRIP)

        assert stack.id == 1
        assert stack.name == TRIP

    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(id=8, name=TAXES)

        stack = StackDTO.model_validate(record)

        assert stack.id == 4 + 4  # the record's id
        assert stack.name == TAXES

    @staticmethod
    def test_missing_name_raises() -> None:
        with pytest.raises(ValidationError):
            StackDTO(id=1)


class TestStackSummary:
    @staticmethod
    def test_carries_a_count() -> None:
        summary = StackSummary(id=1, name=TRIP, file_count=4)

        assert summary.file_count == 2 + 2  # four files sit in it

    @staticmethod
    def test_is_frozen() -> None:
        summary = StackSummary(id=1, name=TRIP, file_count=0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            summary.file_count = 1

    @staticmethod
    def test_equality_is_by_value() -> None:
        left = StackSummary(id=1, name=TRIP, file_count=2)
        right = StackSummary(id=1, name=TRIP, file_count=2)

        assert left == right


class TestStackErrors:
    @staticmethod
    def test_not_found_is_an_exception() -> None:
        with pytest.raises(StackNotFoundError):
            raise StackNotFoundError(StackNotFoundError.__doc__)

    @staticmethod
    def test_invalid_name_is_a_value_error() -> None:
        with pytest.raises(ValueError, match=TRIP):
            raise InvalidStackNameError(TRIP)
