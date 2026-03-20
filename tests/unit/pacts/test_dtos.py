"""Tests for pacts DTOs, dataclasses, and exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from acervus.pacts.dataclasses import FileInfo, ScanResult
from acervus.pacts.dtos import FileDTO, MarkDTO, RootDTO, StackDTO
from acervus.pacts.exceptions import NotFoundError

SAMPLE_ALIAS = "docs"
SAMPLE_PATH = "/home/user/docs"
SAMPLE_RELATIVE_PATH = "todo.txt"
SAMPLE_NAME = "urgent"
SAMPLE_STACK_NAME = "project-x"
SAMPLE_SIZE = 1024
SAMPLE_MTIME = 1234567890.0
SAMPLE_ERROR_MESSAGE = "Root not found"
SAMPLE_DATETIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class TestRootDTO:
    @staticmethod
    def test_from_attributes():
        @dataclass
        class FakeRoot:
            id: int
            alias: str
            path: str

        fake = FakeRoot(id=1, alias=SAMPLE_ALIAS, path=SAMPLE_PATH)
        dto = RootDTO.model_validate(fake)

        assert dto.id == 1
        assert dto.alias == SAMPLE_ALIAS
        assert dto.path == SAMPLE_PATH

    @staticmethod
    def test_fields():
        dto = RootDTO(id=1, alias=SAMPLE_ALIAS, path=SAMPLE_PATH)

        assert dto.id == 1
        assert dto.alias == SAMPLE_ALIAS
        assert dto.path == SAMPLE_PATH


class TestFileDTO:
    @staticmethod
    def test_from_attributes():
        @dataclass
        class FakeFile:  # pylint: disable=duplicate-code
            id: int
            root_id: int
            relative_path: str
            size: int
            mtime: datetime

        fake = FakeFile(
            id=1,
            root_id=1,
            relative_path=SAMPLE_RELATIVE_PATH,
            size=SAMPLE_SIZE,
            mtime=SAMPLE_DATETIME,
        )
        dto = FileDTO.model_validate(fake)

        assert dto.id == 1
        assert dto.root_id == 1
        assert dto.relative_path == SAMPLE_RELATIVE_PATH
        assert dto.size == SAMPLE_SIZE
        assert dto.mtime == SAMPLE_DATETIME

    @staticmethod
    def test_fields():
        dto = FileDTO(
            id=1,
            root_id=1,
            relative_path=SAMPLE_RELATIVE_PATH,
            size=SAMPLE_SIZE,
            mtime=SAMPLE_DATETIME,
        )

        assert dto.id == 1
        assert dto.relative_path == SAMPLE_RELATIVE_PATH


class TestMarkDTO:
    @staticmethod
    def test_from_attributes():
        @dataclass
        class FakeMark:
            id: int
            name: str

        fake = FakeMark(id=1, name=SAMPLE_NAME)
        dto = MarkDTO.model_validate(fake)

        assert dto.id == 1
        assert dto.name == SAMPLE_NAME


class TestStackDTO:
    @staticmethod
    def test_from_attributes():
        @dataclass
        class FakeStack:
            id: int
            name: str

        fake = FakeStack(id=1, name=SAMPLE_STACK_NAME)
        dto = StackDTO.model_validate(fake)

        assert dto.id == 1
        assert dto.name == SAMPLE_STACK_NAME


class TestFileInfo:
    @staticmethod
    def test_creation():
        info = FileInfo(
            relative_path=Path(SAMPLE_RELATIVE_PATH),
            size=SAMPLE_SIZE,
            mtime=SAMPLE_MTIME,
        )

        assert info.relative_path == Path(SAMPLE_RELATIVE_PATH)
        assert info.size == SAMPLE_SIZE
        assert info.mtime == pytest.approx(SAMPLE_MTIME)


class TestScanResult:
    @staticmethod
    def test_creation():
        added = 5
        removed = 2
        updated = 1
        result = ScanResult(added=added, removed=removed, updated=updated)

        assert result.added == added
        assert result.removed == removed
        assert result.updated == updated


class TestNotFoundError:
    @staticmethod
    def test_is_exception():
        with pytest.raises(NotFoundError):
            raise NotFoundError

    @staticmethod
    def test_message():
        error = NotFoundError(SAMPLE_ERROR_MESSAGE)

        assert str(error) == SAMPLE_ERROR_MESSAGE
