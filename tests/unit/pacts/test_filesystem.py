"""Tests for the filesystem port contracts in pacts."""

import dataclasses
from pathlib import Path

import pytest

from acervus.pacts.filesystem import FileInfo

MTIME = 1.5


class TestFileInfo:
    @staticmethod
    def test_fields() -> None:
        info = FileInfo(relative_path=Path("notes/todo.md"), size=1024, mtime=MTIME)

        assert info.relative_path == Path("notes/todo.md")
        assert info.size == 1000 + 24  # a kilobyte
        assert info.mtime == pytest.approx(MTIME)

    @staticmethod
    def test_is_frozen() -> None:
        info = FileInfo(relative_path=Path("notes/todo.md"), size=1024, mtime=MTIME)

        with pytest.raises(dataclasses.FrozenInstanceError):
            info.size = 0

    @staticmethod
    def test_equality_is_by_value() -> None:
        left = FileInfo(relative_path=Path("a.txt"), size=1, mtime=1.0)
        right = FileInfo(relative_path=Path("a.txt"), size=1, mtime=1.0)

        assert left == right
