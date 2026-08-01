"""Tests for the scan service in mills."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from acervus.mills.file import FileService, ScanService
from acervus.pacts.file import FileDTO, FileRepositoryProtocol, ScanResult
from acervus.pacts.filesystem import FileInfo, FilesystemReaderProtocol
from acervus.pacts.root import RootDTO, RootNotFoundError, RootRepositoryProtocol
from acervus.pacts.transaction import TransactionProtocol

ALIAS = "docs"
ROOT = RootDTO(id=7, alias=ALIAS, path=Path("/home/user/docs"))
NOTES = Path("notes/plan.md")
INBOX = Path("inbox.md")
SIZE = 12
GROWN_SIZE = 99
MTIME = 1.5
LATER_MTIME = 2.5

NOTES_ON_DISK = FileInfo(relative_path=NOTES, size=SIZE, mtime=MTIME)
INBOX_ON_DISK = FileInfo(relative_path=INBOX, size=SIZE, mtime=MTIME)
NOTES_RESIZED = FileInfo(relative_path=NOTES, size=GROWN_SIZE, mtime=MTIME)
NOTES_TOUCHED = FileInfo(relative_path=NOTES, size=SIZE, mtime=LATER_MTIME)

NOTES_INDEXED = FileDTO(
    id=1, root_id=ROOT.id, relative_path=NOTES, size=SIZE, mtime=MTIME
)
INBOX_INDEXED = FileDTO(
    id=2, root_id=ROOT.id, relative_path=INBOX, size=SIZE, mtime=MTIME
)

NOTES_WRITE = {"root_id": ROOT.id, "relative_path": NOTES, "size": SIZE, "mtime": MTIME}
INBOX_WRITE = {"root_id": ROOT.id, "relative_path": INBOX, "size": SIZE, "mtime": MTIME}
NOTES_RESIZED_WRITE = {
    "root_id": ROOT.id,
    "relative_path": NOTES,
    "size": GROWN_SIZE,
    "mtime": MTIME,
}


@pytest.fixture(name="files")
def files_fixture():
    repository = Mock(spec=FileRepositoryProtocol)
    repository.list_by_root.return_value = []
    return repository


@pytest.fixture(name="roots")
def roots_fixture():
    repository = Mock(spec=RootRepositoryProtocol)
    repository.read_by_alias.return_value = ROOT
    return repository


@pytest.fixture(name="filesystem")
def filesystem_fixture():
    reader = Mock(spec=FilesystemReaderProtocol)
    reader.walk.return_value = iter(())
    return reader


@pytest.fixture(name="transaction")
def transaction_fixture():
    return MagicMock(spec=TransactionProtocol)


@pytest.fixture(name="service")
def service_fixture(files, roots, filesystem, transaction):
    return ScanService(files, roots, filesystem, transaction)


class TestFileServiceListAll:
    @staticmethod
    def test_it_asks_the_repository_for_everything(files):
        files.list_all.return_value = [NOTES_INDEXED, INBOX_INDEXED]

        assert FileService(files).list_all() == [NOTES_INDEXED, INBOX_INDEXED]

        files.list_all.assert_called_once_with(None)

    @staticmethod
    def test_it_passes_a_root_filter_through(files):
        files.list_all.return_value = [NOTES_INDEXED]

        assert FileService(files).list_all(ROOT.id) == [NOTES_INDEXED]

        files.list_all.assert_called_once_with(ROOT.id)

    @staticmethod
    def test_an_empty_index_lists_nothing(files):
        files.list_all.return_value = []

        assert FileService(files).list_all() == []


class TestScan:
    @staticmethod
    def test_it_looks_the_root_up_by_alias(service, roots):
        service.scan(ALIAS)

        roots.read_by_alias.assert_called_once_with(ALIAS)

    @staticmethod
    def test_it_walks_the_path_the_root_names(service, filesystem):
        service.scan(ALIAS)

        filesystem.walk.assert_called_once_with(ROOT.path)

    @staticmethod
    def test_it_reads_the_index_for_the_root_it_found(service, files):
        service.scan(ALIAS)

        files.list_by_root.assert_called_once_with(ROOT.id)

    @staticmethod
    def test_it_scans_inside_one_transaction(service, filesystem, transaction):
        filesystem.walk.return_value = iter((NOTES_ON_DISK,))

        service.scan(ALIAS)

        transaction.atomic.assert_called_once_with()
        transaction.atomic.return_value.__enter__.assert_called_once_with()
        transaction.atomic.return_value.__exit__.assert_called_once()

    @staticmethod
    def test_an_unknown_alias_raises(service, roots, files):
        roots.read_by_alias.side_effect = RootNotFoundError(ALIAS)

        with pytest.raises(RootNotFoundError):
            service.scan(ALIAS)

        files.upsert_many.assert_not_called()
        files.delete_many.assert_not_called()


class TestScanAdds:
    @staticmethod
    def test_it_indexes_every_file_it_walks(service, files, filesystem):
        filesystem.walk.return_value = iter((NOTES_ON_DISK, INBOX_ON_DISK))

        service.scan(ALIAS)

        files.upsert_many.assert_called_once_with([NOTES_WRITE, INBOX_WRITE])

    @staticmethod
    def test_it_counts_a_file_the_index_lacks(service, filesystem):
        filesystem.walk.return_value = iter((NOTES_ON_DISK, INBOX_ON_DISK))

        assert service.scan(ALIAS).added == 1 + 1  # both walked files are new

    @staticmethod
    def test_it_does_not_count_an_already_indexed_file(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED]
        filesystem.walk.return_value = iter((NOTES_ON_DISK, INBOX_ON_DISK))

        assert service.scan(ALIAS).added == 1

    @staticmethod
    def test_an_empty_root_writes_nothing(service, files):
        result = service.scan(ALIAS)

        files.upsert_many.assert_not_called()
        assert result.added == 0


class TestScanRemoves:
    @staticmethod
    def test_it_deletes_a_file_the_root_no_longer_has(service, files):
        files.list_by_root.return_value = [NOTES_INDEXED]

        service.scan(ALIAS)

        files.delete_many.assert_called_once_with([NOTES_INDEXED.id])

    @staticmethod
    def test_it_counts_the_removal(service, files):
        files.list_by_root.return_value = [NOTES_INDEXED, INBOX_INDEXED]

        assert service.scan(ALIAS).removed == 1 + 1  # both indexed files are gone

    @staticmethod
    def test_it_keeps_a_file_the_root_still_has(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED, INBOX_INDEXED]
        filesystem.walk.return_value = iter((NOTES_ON_DISK,))

        result = service.scan(ALIAS)

        files.delete_many.assert_called_once_with([INBOX_INDEXED.id])
        assert result.removed == 1


class TestScanUpdates:
    @staticmethod
    def test_it_rewrites_a_file_whose_size_changed(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED]
        filesystem.walk.return_value = iter((NOTES_RESIZED,))

        result = service.scan(ALIAS)

        files.upsert_many.assert_called_once_with([NOTES_RESIZED_WRITE])
        assert result.updated == 1

    @staticmethod
    def test_it_rewrites_a_file_whose_mtime_changed(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED]
        filesystem.walk.return_value = iter((NOTES_TOUCHED,))

        assert service.scan(ALIAS).updated == 1

    @staticmethod
    def test_an_update_is_not_an_addition(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED]
        filesystem.walk.return_value = iter((NOTES_RESIZED,))

        assert service.scan(ALIAS).added == 0

    @staticmethod
    def test_it_leaves_an_unchanged_file_alone(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED]
        filesystem.walk.return_value = iter((NOTES_ON_DISK,))

        result = service.scan(ALIAS)

        files.upsert_many.assert_not_called()
        files.delete_many.assert_not_called()
        assert result == ScanResult(added=0, removed=0, updated=0)


class TestScanTogether:
    @staticmethod
    def test_counts_add_up(service, files, filesystem):
        gone = FileDTO(
            id=3, root_id=ROOT.id, relative_path=Path("gone.md"), size=SIZE, mtime=MTIME
        )
        files.list_by_root.return_value = [NOTES_INDEXED, gone]
        filesystem.walk.return_value = iter((NOTES_RESIZED, INBOX_ON_DISK))

        result = service.scan(ALIAS)

        assert result.added == 1  # inbox
        assert result.removed == 1  # gone.md
        assert result.updated == 1  # notes grew

    @staticmethod
    def test_it_writes_the_new_and_the_changed_together(service, files, filesystem):
        files.list_by_root.return_value = [NOTES_INDEXED]
        filesystem.walk.return_value = iter((NOTES_RESIZED, INBOX_ON_DISK))

        service.scan(ALIAS)

        files.upsert_many.assert_called_once_with([NOTES_RESIZED_WRITE, INBOX_WRITE])
