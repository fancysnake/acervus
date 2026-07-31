"""Tests for the root noun contracts in pacts."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from acervus.pacts.root import RootDTO, RootNotFoundError

DOCS = "docs"
PHOTOS = "photos"


class TestRootDTO:
    @staticmethod
    def test_valid() -> None:
        root = RootDTO(id=1, alias=DOCS, path=Path("/home/user/docs"))

        assert root.id == 1
        assert root.alias == DOCS
        assert root.path == Path("/home/user/docs")

    @staticmethod
    def test_path_coerced_from_string() -> None:
        root = RootDTO.model_validate(
            {"id": 1, "alias": DOCS, "path": "/home/user/docs"},
        )

        assert root.path == Path("/home/user/docs")

    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(id=7, alias=PHOTOS, path="/home/user/photos")

        root = RootDTO.model_validate(record)

        assert root.id == 3 + 4  # the record's id
        assert root.alias == PHOTOS
        assert root.path == Path("/home/user/photos")

    @staticmethod
    def test_missing_alias_raises() -> None:
        with pytest.raises(ValidationError):
            RootDTO(id=1, path=Path("/tmp"))

    @staticmethod
    def test_missing_path_raises() -> None:
        with pytest.raises(ValidationError):
            RootDTO(id=1, alias=DOCS)


class TestRootNotFoundError:
    @staticmethod
    def test_is_an_exception() -> None:
        with pytest.raises(RootNotFoundError):
            raise RootNotFoundError(RootNotFoundError.__doc__)
