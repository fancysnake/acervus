"""Business operations that reconcile the index against the filesystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from acervus.pacts.file import (
    FileServiceProtocol,
    FileWrite,
    ScanResult,
    ScanServiceProtocol,
)

if TYPE_CHECKING:
    from acervus.pacts.file import FileDTO, FileRepositoryProtocol
    from acervus.pacts.filesystem import FileInfo, FilesystemReaderProtocol
    from acervus.pacts.root import RootRepositoryProtocol
    from acervus.pacts.transaction import TransactionProtocol


class FileService(FileServiceProtocol):
    """Reads the indexed files."""

    def __init__(self, files: FileRepositoryProtocol) -> None:
        self._files = files

    def list_all(self, root_id: int | None = None) -> list[FileDTO]:
        """Return indexed files, narrowed to one root when given an id.

        Returns:
            The matching files, ordered by root and then relative path.
        """
        return self._files.list_all(root_id)


class ScanService(ScanServiceProtocol):
    """Walks a root and brings the index into line with what is there."""

    def __init__(
        self,
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

        An alias no root holds raises ``RootNotFoundError`` out of the
        repository, rolling the scan back before it writes anything.

        Returns:
            How many files the index gained, lost and rewrote.
        """
        with self._transaction.atomic():
            root = self._roots.read_by_alias(alias)
            indexed = {
                file.relative_path: file for file in self._files.list_by_root(root.id)
            }
            found = {
                info.relative_path: info for info in self._filesystem.walk(root.path)
            }

            if gone := [file.id for path, file in indexed.items() if path not in found]:
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
