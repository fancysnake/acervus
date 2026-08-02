"""Boundary contracts for the file noun."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterable


class Bare(Enum):
    """The files carrying no mark at all, or sitting in no stack at all."""

    BARE = "bare"


BARE = Bare.BARE

# One narrowing of a listing: a name to match, BARE, or None for no narrowing.
type Narrowing = str | Bare | None


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

    An empty filter lists everything, and the narrowings combine. Each of
    ``mark`` and ``stack`` is one choice with three outcomes: ``None`` does not
    narrow at all, a name keeps the files carrying it or sitting in it, and
    ``BARE`` keeps only the files that carry no mark, or sit in no stack.
    """

    root_id: int | None = None
    mark: Narrowing = None
    stack: Narrowing = None


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
