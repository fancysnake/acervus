"""Tests for the mark noun contracts in pacts."""

from types import SimpleNamespace

from acervus.pacts.mark import MarkDTO

HOLIDAY = "holiday"


class TestMarkDTO:
    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(id=9, name=HOLIDAY)

        mark = MarkDTO.model_validate(record)

        assert mark.id == 4 + 5  # the record's id
        assert mark.name == HOLIDAY
