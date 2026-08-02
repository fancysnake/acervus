"""Tests for the file noun contracts in pacts."""

import dataclasses
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from acervus.pacts.file import FileDTO, ScanResult

MTIME = 1.5


class TestFileDTO:
    @staticmethod
    def test_valid() -> None:
        file = FileDTO(
            id=1, root_id=2, relative_path=Path("notes/todo.md"), size=12, mtime=MTIME
        )

        assert file.relative_path == Path("notes/todo.md")
        assert file.size == 6 + 6  # twelve bytes
        assert file.mtime == pytest.approx(MTIME)

    @staticmethod
    def test_from_attributes() -> None:
        record = SimpleNamespace(
            id=1, root_id=2, relative_path="notes/todo.md", size=12, mtime=MTIME
        )

        file = FileDTO.model_validate(record)

        assert file.relative_path == Path("notes/todo.md")
        assert file.root_id == 1 + 1  # the record's root_id

    @staticmethod
    def test_missing_root_id_raises() -> None:
        with pytest.raises(ValidationError):
            FileDTO(id=1, relative_path=Path("a.txt"), size=1, mtime=1.0)


class TestScanResult:
    @staticmethod
    def test_counts() -> None:
        result = ScanResult(added=3, removed=1, updated=2)

        assert result.added == 1 + 2  # three new files
        assert result.removed == 1
        assert result.updated == 1 + 1  # two changed files

    @staticmethod
    def test_is_frozen() -> None:
        result = ScanResult(added=0, removed=0, updated=0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.added = 1
