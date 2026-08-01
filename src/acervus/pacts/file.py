"""Boundary contracts for the file noun."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterable


class FileMissingError(Exception):
    """No file matches the requested identifier."""


class FileDTO(BaseModel):
    """A file discovered under a root, as read from the index."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    root_id: int
    relative_path: Path
    size: int
    mtime: float


class FileWrite(TypedDict):
    """The fields needed to create or update a file."""

    root_id: int
    relative_path: Path
    size: int
    mtime: float


@dataclass(frozen=True, slots=True)
class FileFilter:
    """How a file listing is narrowed.

    An empty filter lists everything, and the narrowings combine. Naming a
    mark and asking for unmarked files at once is self-contradictory and lists
    nothing, which is the honest answer rather than an error; the same goes
    for a stack and unstacked.
    """

    root_id: int | None = None
    mark: str | None = None
    unmarked: bool = False
    stack: str | None = None
    unstacked: bool = False


@dataclass(frozen=True, slots=True)
class ScanResult:
    """How a scan changed the index."""

    added: int
    removed: int
    updated: int


class FileRepositoryProtocol(Protocol):
    """Data access for files."""

    def list_all(self, scope: FileFilter | None = None) -> list[FileDTO]:
        """Return indexed files, narrowed by the filter when one is given."""

    def list_by_root(self, root_id: int) -> list[FileDTO]:
        """Return every indexed file under this root."""

    def upsert_many(self, files: Iterable[FileWrite]) -> list[FileDTO]:
        """Insert or update files by root and relative path, and return them."""

    def delete_many(self, file_ids: Iterable[int]) -> None:
        """Delete the files with these ids."""


class FileServiceProtocol(Protocol):
    """Business operations on indexed files."""

    def list_all(self, scope: FileFilter | None = None) -> list[FileDTO]:
        """Return indexed files, narrowed by the filter when one is given."""


class ScanServiceProtocol(Protocol):
    """Business operations that reconcile the index against the filesystem."""

    def scan(self, alias: str) -> ScanResult:
        """Walk the root with this alias and reconcile the index against it."""
