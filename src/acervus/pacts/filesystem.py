"""Boundary contracts for the filesystem port."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class RootLostError(Exception):
    """The root went out from under the walk before it could finish."""


@dataclass(frozen=True, slots=True)
class FileInfo:
    """A file as found on disk, addressed relative to the root holding it."""

    relative_path: Path
    size: int
    mtime: float


@dataclass(frozen=True, slots=True)
class Traversal:
    """What one walk of a root saw, and which parts of it it could not see.

    A caller reconciling an index against a root deletes what the root no
    longer holds, so it has to tell "this file is gone" apart from "this file
    was never looked at". ``unread`` names the directories the walk could not
    open, relative to the root, and nothing below them was looked at.
    """

    files: tuple[FileInfo, ...]
    unread: tuple[Path, ...]


class FilesystemReaderProtocol(Protocol):
    """Read-only traversal of a directory tree."""

    @staticmethod
    def exists(root: Path) -> bool:
        """Return whether this root is there to be walked."""

    def walk(self, root: Path) -> Traversal:
        """Return every file below ``root``, and the directories it could not read.

        Raises:
            RootLostError: The root itself could not be read, so the walk saw
                nothing and cannot say what the root holds.
        """
