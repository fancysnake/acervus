"""Tests for the root noun contracts in pacts."""

from pathlib import Path
from types import SimpleNamespace

from acervus.pacts.root import RootDTO

PHOTOS = "photos"


class TestRootDTO:
    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(id=7, alias=PHOTOS, path="/home/user/photos")

        root = RootDTO.model_validate(record)

        assert root.id == 3 + 4  # the record's id
        assert root.alias == PHOTOS
        assert root.path == Path("/home/user/photos")
