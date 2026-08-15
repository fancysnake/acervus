"""Business operations that reconcile the index against the filesystem."""

from typing import TYPE_CHECKING

from acervus.pacts.file import FileWrite, ScanResult, ScanServiceProtocol
from acervus.pacts.filesystem import RootLostError
from acervus.pacts.root import RootUnavailableError

if TYPE_CHECKING:
    from pathlib import Path

    from acervus.pacts.file import FileDTO, FileRepositoryProtocol
    from acervus.pacts.filesystem import FileInfo, FilesystemReaderProtocol, Traversal
    from acervus.pacts.root import RootRepositoryProtocol
    from acervus.pacts.transaction import TransactionProtocol

UNAVAILABLE = "Root {alias!r} is not at {path}, so nothing was scanned."
LOST = "Root {alias!r} stopped being readable at {path}, so nothing was changed."


class ScanService(ScanServiceProtocol):
    """Walks a root and brings the index into line with what is there."""

    def __init__(
        self,
        *,
        files: FileRepositoryProtocol,
        roots: RootRepositoryProtocol,
        filesystem: FilesystemReaderProtocol,
        transaction: TransactionProtocol,
    ) -> None:
        self._files = files
        self._roots = roots
        self._filesystem = filesystem
        self._transaction = transaction

    def scan(self, alias: str) -> ScanResult:
        """Walk the root with this alias and reconcile the index against it.

        A file the root has but the index lacks is inserted. A file whose size
        or mtime has moved is rewritten. A file the index holds but the root no
        longer has is deleted. A file both agree on is left untouched, so a
        rescan of a quiet root writes nothing at all.

        Deleting is the one direction that loses work, since a file's marks and
        its stack go with it and no rescan brings them back. So only a file the
        walk actually looked for and did not find counts as gone: a directory
        the walk could not open leaves everything indexed beneath it alone.

        An alias no root holds raises ``RootNotFoundError`` out of the
        repository, rolling the scan back before it writes anything.

        Returns:
            How many files the index gained, lost and rewrote.

        Raises:
            RootUnavailableError: The root is not there to read, or stopped
                being readable while it was being walked. Either way the walk
                cannot say what the root holds, and reading that as an empty
                root would delete every file indexed under it.
        """
        with self._transaction.atomic():
            root = self._roots.read_by_alias(alias)
            if not self._filesystem.exists(root.path):
                message = UNAVAILABLE.format(alias=alias, path=root.path)
                raise RootUnavailableError(message)
            indexed = {
                file.relative_path: file for file in self._files.list_by_root(root.id)
            }
            traversal = self._look(alias, path=root.path)
            found = {info.relative_path: info for info in traversal.files}

            if gone := [
                file.id
                for path, file in indexed.items()
                if path not in found and not self._unread(path, traversal.unread)
            ]:
                self._files.delete_many(gone)

            added = 0
            updated = 0
            written: list[FileWrite] = []
            for path, info in found.items():
                if (existing := indexed.get(path)) is None:
                    added += 1
                elif self._moved(existing, info):
                    updated += 1
                else:
                    continue
                written.append(self._write(root.id, info))
            if written:
                self._files.upsert_many(written)

            return ScanResult(added=added, removed=len(gone), updated=updated)

    def _look(self, alias: str, *, path: Path) -> Traversal:
        """Walk the root, saying so in the caller's terms if it goes.

        Returns:
            What the walk saw.

        Raises:
            RootUnavailableError: The root stopped being readable during the
                walk, so what it holds is unknown rather than nothing.
        """
        try:
            return self._filesystem.walk(path)
        except RootLostError as error:
            message = LOST.format(alias=alias, path=path)
            raise RootUnavailableError(message) from error

    @staticmethod
    def _unread(path: Path, unread: tuple[Path, ...]) -> bool:
        """Say whether this indexed path sits under a directory nothing read.

        Returns:
            Whether the walk never looked where this file is indexed, in which
            case its absence from the walk says nothing about its absence from
            the disk.
        """
        return any(path.is_relative_to(directory) for directory in unread)

    @staticmethod
    def _moved(indexed: FileDTO, found: FileInfo) -> bool:
        return indexed.size != found.size or indexed.mtime != found.mtime

    @staticmethod
    def _write(root_id: int, info: FileInfo) -> FileWrite:
        return FileWrite(
            root_id=root_id,
            relative_path=info.relative_path,
            size=info.size,
            mtime=info.mtime,
        )
