"""Reading a directory tree with the standard library."""

from typing import TYPE_CHECKING

from acervus.pacts.filesystem import FileInfo, FilesystemReaderProtocol

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class PathlibFilesystemReader(FilesystemReaderProtocol):
    """Walks a directory tree, reporting each file as the index sees it."""

    @staticmethod
    def exists(root: Path) -> bool:
        """Return whether this root is there to be walked.

        Returns:
            Whether the path names a directory that can be reached now.
        """
        return root.is_dir()

    def walk(self, root: Path) -> Iterator[FileInfo]:
        """Yield every file below ``root``, skipping directories themselves.

        A root that does not exist yields nothing rather than raising, so a
        scan of a root that has been unmounted or removed reads as empty. A
        broken symlink is skipped for the same reason.

        Yields:
            One entry per file, addressed relative to ``root``.
        """
        for path in root.rglob("*"):
            if path.is_file():
                yield self._describe(path, root)

    @staticmethod
    def _describe(path: Path, root: Path) -> FileInfo:
        stat = path.stat()
        return FileInfo(
            relative_path=path.relative_to(root), size=stat.st_size, mtime=stat.st_mtime
        )
