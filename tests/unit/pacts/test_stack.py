"""Tests for the stack noun contracts in pacts."""

from types import SimpleNamespace

from acervus.pacts.stack import StackDTO

TAXES = "taxes 2026"


class TestStackDTO:
    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(id=8, name=TAXES)

        stack = StackDTO.model_validate(record)

        assert stack.id == 4 + 4  # the record's id
        assert stack.name == TAXES
