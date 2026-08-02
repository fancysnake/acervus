"""Tests for the file noun contracts in pacts."""

from pathlib import Path
from types import SimpleNamespace

from acervus.pacts.file import FileDTO

MTIME = 1.5


class TestFileDTO:
    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(
            id=1, root_id=2, relative_path="notes/todo.md", size=12, mtime=MTIME
        )

        file = FileDTO.model_validate(record)

        assert file.relative_path == Path("notes/todo.md")
        assert file.root_id == 1 + 1  # the record's root_id
