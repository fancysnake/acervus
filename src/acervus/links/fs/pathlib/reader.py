"""Reading a directory tree with the standard library."""

from fnmatch import fnmatch
from pathlib import Path
from stat import S_ISREG
from typing import TYPE_CHECKING

from acervus.pacts.filesystem import (
    FileInfo,
    FilesystemReaderProtocol,
    RootLostError,
    Traversal,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

LOST = "Root {root} could not be read, so nothing under it was walked."


class PathlibFilesystemReader(FilesystemReaderProtocol):
    """Walks a directory tree, reporting each file as the index sees it."""

    def __init__(self, ignore: Iterable[str] = ()) -> None:
        """Take the glob patterns naming what this reader must not report.

        Each pattern is matched against one path component at a time, so
        ``.venv`` names a directory of that name at any depth rather than one
        at the top, and ``*.pyc`` names a file.
        """
        self._ignore = tuple(ignore)

    @staticmethod
    def exists(root: Path) -> bool:
        """Return whether this root is there to be walked.

        Returns:
            Whether the path names a directory that can be reached now.
        """
        return root.is_dir()

    def walk(self, root: Path) -> Traversal:
        """Return every file below ``root``, skipping directories themselves.

        An ignored directory is pruned rather than filtered, so a tree holding
        a virtualenv or a ``node_modules`` costs nothing to skip.

        A broken symlink is passed over, and so is a file that vanishes
        mid-walk: a live tree changes under the walk, and one file going
        missing is not a reason to abandon the rest — it is genuinely not
        there any more.

        A directory that cannot be read is different. Nothing below it was
        looked at, so reporting it as holding no files would tell a caller
        reconciling an index that everything under it had been deleted. It is
        named in ``unread`` instead, and the caller leaves that subtree alone.
        The root itself failing to open is that same case widened to
        everything, so it comes back as ``RootLostError`` rather than as a walk
        that reads as an empty root.

        Returns:
            The files found, and the directories that could not be opened.
        """
        files: list[FileInfo] = []
        unread: list[Path] = []
        for directory, subdirectories, names in root.walk(
            on_error=lambda error: self._passed_over(error, root=root, unread=unread)
        ):
            subdirectories[:] = [
                name for name in subdirectories if not self._ignored(name)
            ]
            for name in names:
                if self._ignored(name):
                    continue
                if (found := self._describe(directory / name, root)) is not None:
                    files.append(found)
        return Traversal(files=tuple(files), unread=tuple(unread))

    @staticmethod
    def _passed_over(error: OSError, *, root: Path, unread: list[Path]) -> None:
        """Record the directory this error was raised over, or give up on the root.

        ``OSError.filename`` is typed loosely enough to be anything, so the
        path is taken back through ``str``: the walk names the directory it
        failed on, and nothing here needs more of it than that.

        Raises:
            RootLostError: The error is the root's own, so there is no subtree
                to pass over and nothing was walked at all.
        """
        named: object = error.filename
        failed = None if named is None else Path(str(named))
        if failed is None or failed == root or not failed.is_relative_to(root):
            message = LOST.format(root=root)
            raise RootLostError(message) from error
        unread.append(failed.relative_to(root))

    def _ignored(self, name: str) -> bool:
        """Return whether this path component is one the reader passes over.

        Returns:
            Whether any ignore pattern matches the name.
        """
        return any(fnmatch(name, pattern) for pattern in self._ignore)

    @staticmethod
    def _describe(path: Path, root: Path) -> FileInfo | None:
        """Return this path as the index sees it.

        One ``stat`` answers both whether the path is a file and how big it
        is, so nothing can change between the two questions.

        Returns:
            The file, or ``None`` if the path is not a readable file.
        """
        try:
            stat = path.stat()
        except OSError:
            return None
        if not S_ISREG(stat.st_mode):
            return None
        return FileInfo(
            relative_path=path.relative_to(root), size=stat.st_size, mtime=stat.st_mtime
        )
