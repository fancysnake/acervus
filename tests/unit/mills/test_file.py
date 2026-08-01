"""Tests for the scan service in mills."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from acervus.mills.file import ScanService
from acervus.pacts.file import FileDTO, FileRepositoryProtocol
from acervus.pacts.filesystem import FileInfo, FilesystemReaderProtocol
from acervus.pacts.root import RootDTO, RootNotFoundError, RootRepositoryProtocol
from acervus.pacts.transaction import TransactionProtocol

ALIAS = "docs"
ROOT = RootDTO(id=7, alias=ALIAS, path=Path("/home/user/docs"))
TODO = Path("notes/todo.md")
INBOX = Path("inbox.md")
SIZE = 12
MTIME = 1.5

TODO_ON_DISK = FileInfo(relative_path=TODO, size=SIZE, mtime=MTIME)
INBOX_ON_DISK = FileInfo(relative_path=INBOX, size=SIZE, mtime=MTIME)
TODO_INDEXED = FileDTO(
    id=1, root_id=ROOT.id, relative_path=TODO, size=SIZE, mtime=MTIME
)

TODO_WRITE = {"root_id": ROOT.id, "relative_path": TODO, "size": SIZE, "mtime": MTIME}
INBOX_WRITE = {"root_id": ROOT.id, "relative_path": INBOX, "size": SIZE, "mtime": MTIME}


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
    def test_it_indexes_every_file_it_walks(service, files, filesystem):
        filesystem.walk.return_value = iter((TODO_ON_DISK, INBOX_ON_DISK))

        service.scan(ALIAS)

        files.upsert_many.assert_called_once_with([TODO_WRITE, INBOX_WRITE])

    @staticmethod
    def test_it_counts_a_file_the_index_lacks_as_added(service, filesystem):
        filesystem.walk.return_value = iter((TODO_ON_DISK, INBOX_ON_DISK))

        assert service.scan(ALIAS).added == 1 + 1  # both walked files are new

    @staticmethod
    def test_it_does_not_count_an_already_indexed_file(service, files, filesystem):
        files.list_by_root.return_value = [TODO_INDEXED]
        filesystem.walk.return_value = iter((TODO_ON_DISK, INBOX_ON_DISK))

        assert service.scan(ALIAS).added == 1

    @staticmethod
    def test_it_reports_no_removals_or_updates_yet(service, filesystem):
        filesystem.walk.return_value = iter((TODO_ON_DISK,))

        result = service.scan(ALIAS)

        assert result.removed == 0
        assert result.updated == 0

    @staticmethod
    def test_an_empty_root_writes_nothing(service, files):
        result = service.scan(ALIAS)

        files.upsert_many.assert_not_called()
        assert result.added == 0

    @staticmethod
    def test_it_reads_the_index_for_the_root_it_found(service, files):
        service.scan(ALIAS)

        files.list_by_root.assert_called_once_with(ROOT.id)

    @staticmethod
    def test_it_scans_inside_one_transaction(service, filesystem, transaction):
        filesystem.walk.return_value = iter((TODO_ON_DISK,))

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
