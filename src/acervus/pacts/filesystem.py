"""Boundary contracts for the filesystem port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileInfo:
    """A file as found on disk, addressed relative to the root holding it."""

    relative_path: Path
    size: int
    mtime: float


class FilesystemReaderProtocol(Protocol):
    """Read-only traversal of a directory tree."""

    def walk(self, root: Path) -> Iterator[FileInfo]:
        """Yield every file below ``root``, skipping directories themselves."""
