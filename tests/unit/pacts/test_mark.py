"""Tests for the mark noun contracts in pacts."""

import dataclasses
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from acervus.pacts.mark import (
    InvalidMarkNameError,
    MarkDTO,
    MarkNotFoundError,
    MarkSummary,
)

INVOICE = "invoice"
HOLIDAY = "holiday"


class TestMarkDTO:
    @staticmethod
    def test_valid() -> None:
        mark = MarkDTO(id=1, name=INVOICE)

        assert mark.id == 1
        assert mark.name == INVOICE

    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(id=9, name=HOLIDAY)

        mark = MarkDTO.model_validate(record)

        assert mark.id == 4 + 5  # the record's id
        assert mark.name == HOLIDAY

    @staticmethod
    def test_missing_name_raises() -> None:
        with pytest.raises(ValidationError):
            MarkDTO(id=1)


class TestMarkSummary:
    @staticmethod
    def test_carries_a_count() -> None:
        summary = MarkSummary(id=1, name=INVOICE, file_count=3)

        assert summary.file_count == 1 + 2  # three files carry it

    @staticmethod
    def test_is_frozen() -> None:
        summary = MarkSummary(id=1, name=INVOICE, file_count=0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            summary.file_count = 1

    @staticmethod
    def test_equality_is_by_value() -> None:
        left = MarkSummary(id=1, name=INVOICE, file_count=2)
        right = MarkSummary(id=1, name=INVOICE, file_count=2)

        assert left == right


class TestMarkErrors:
    @staticmethod
    def test_not_found_is_an_exception() -> None:
        with pytest.raises(MarkNotFoundError):
            raise MarkNotFoundError(MarkNotFoundError.__doc__)

    @staticmethod
    def test_invalid_name_is_a_value_error() -> None:
        with pytest.raises(ValueError, match=INVOICE):
            raise InvalidMarkNameError(INVOICE)
