"""Business operations that reconcile the index against the filesystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from acervus.pacts.file import FileWrite, ScanResult, ScanServiceProtocol

if TYPE_CHECKING:
    from acervus.pacts.file import FileRepositoryProtocol
    from acervus.pacts.filesystem import FilesystemReaderProtocol
    from acervus.pacts.root import RootRepositoryProtocol
    from acervus.pacts.transaction import TransactionProtocol


class ScanService(ScanServiceProtocol):
    """Walks a root and writes what it finds into the index."""

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
        """Walk the root with this alias and index every file below it.

        This pass only inserts. Files the index holds but the root no longer
        has are left alone, and a file whose size or mtime moved is rewritten
        without being reported as changed.

        An alias no roots holds raises ``RootNotFoundError`` out of the
        repository, rolling the scan back before it writes anything.

        Returns:
            How many files the index gained. Removals and updates read zero.
        """
        with self._transaction.atomic():
            root = self._roots.read_by_alias(alias)
            indexed = {file.relative_path for file in self._files.list_by_root(root.id)}
            found = [
                FileWrite(
                    root_id=root.id,
                    relative_path=info.relative_path,
                    size=info.size,
                    mtime=info.mtime,
                )
                for info in self._filesystem.walk(root.path)
            ]
            if found:
                self._files.upsert_many(found)
            added = sum(1 for file in found if file["relative_path"] not in indexed)
            return ScanResult(added=added, removed=0, updated=0)
