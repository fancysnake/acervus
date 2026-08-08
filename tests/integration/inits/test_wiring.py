"""Tests for the containers in inits, against a real database."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest

from acervus.inits.repositories import Repositories
from acervus.inits.services import Services
from acervus.links.db.sqlalchemy import (
    FileRepository,
    RootRepository,
    SessionTransaction,
)
from acervus.mills.root import RootService
from acervus.pacts.root import RootUnavailableError

NOTES = "notes"
NOTES_PATH = Path("/home/user/notes")
ARCHIVE = "archive"
ARCHIVE_PATH = Path("/home/user/archive")
CONTENT = "hello"
LONGER = "hello again, and then some"
INBOX = "inbox.md"


@pytest.fixture(name="db_path")
def db_path_fixture(tmp_path):
    return tmp_path / "state" / "acervus.db"


@pytest.fixture(name="repositories")
def repositories_fixture(db_path):
    with closing(Repositories(db_path)) as repositories:
        yield repositories


@pytest.fixture(name="services")
def services_fixture(repositories):
    return Services(repositories)


@pytest.fixture(name="tree")
def tree_fixture(tmp_path):
    tree = tmp_path / "notes"
    tree.mkdir()
    (tree / INBOX).write_text(CONTENT)
    return tree


class TestRepositories:
    @staticmethod
    def test_the_database_file_is_created_on_first_use(db_path, repositories):
        assert not db_path.exists()

        repositories.roots.list_all()

        assert db_path.exists()

    @staticmethod
    def test_it_builds_the_parent_directory(db_path, repositories):
        repositories.roots.list_all()

        assert db_path.parent.is_dir()

    @staticmethod
    def test_it_hands_out_repositories(repositories):
        assert isinstance(repositories.roots, RootRepository)
        assert isinstance(repositories.files, FileRepository)

    @staticmethod
    def test_it_hands_out_a_transaction(repositories):
        assert isinstance(repositories.transaction, SessionTransaction)

    @staticmethod
    def test_every_repository_shares_one_session(repositories):
        root = repositories.roots.upsert_many([{"alias": NOTES, "path": NOTES_PATH}])[0]

        assert repositories.files.list_by_root(root.id) == []

    @staticmethod
    def test_the_session_is_opened_once(repositories):
        assert repositories.session is repositories.session


class TestClosingTheContainer:
    @staticmethod
    def test_closing_an_unused_container_creates_nothing(db_path):
        Repositories(db_path).close()

        assert not db_path.exists()

    @staticmethod
    def test_closing_twice_does_nothing_the_second_time(db_path):
        container = Repositories(db_path)
        container.roots.list_all()

        container.close()
        container.close()

        assert db_path.exists()

    @staticmethod
    def test_a_container_used_after_a_close_opens_a_new_session(db_path):
        container = Repositories(db_path)
        opened = container.session

        container.close()

        assert container.session is not opened
        container.close()


class TestServices:
    @staticmethod
    def test_it_hands_out_services(services):
        assert isinstance(services.roots, RootService)

    @staticmethod
    def test_the_services_are_cached(services):
        assert services.roots is services.roots

    @staticmethod
    def test_sync_reaches_the_database(db_path, services):
        synced = services.roots.sync({NOTES: NOTES_PATH, ARCHIVE: ARCHIVE_PATH})

        assert [root.alias for root in synced] == [ARCHIVE, NOTES]
        with closing(Repositories(db_path)) as reopened:
            assert [root.alias for root in reopened.roots.list_all()] == [
                ARCHIVE,
                NOTES,
            ]

    @staticmethod
    def test_sync_drops_a_root_the_config_no_longer_names(db_path, services):
        services.roots.sync({NOTES: NOTES_PATH, ARCHIVE: ARCHIVE_PATH})

        services.roots.sync({NOTES: NOTES_PATH})

        with closing(Repositories(db_path)) as reopened:
            assert [root.alias for root in reopened.roots.list_all()] == [NOTES]


# The interface runs the scan on a thread, so it must work from one, and what
# it writes must be visible to the session the interface is reading through.
class TestScanningOffTheCallersThread:
    @staticmethod
    def test_it_scans_from_another_thread(services, tree):
        services.roots.sync({NOTES: tree})

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(services.scan.scan, NOTES).result()

        assert result.added == 1

    @staticmethod
    def test_the_shared_session_sees_what_the_thread_wrote(services, tree):
        root = services.roots.sync({NOTES: tree})[0]

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(services.scan.scan, NOTES).result()

        assert len(services.files.list_by_root(root.id)) == 1

    @staticmethod
    def test_the_shared_session_sees_what_the_thread_rewrote(services, tree):
        root = services.roots.sync({NOTES: tree})[0]
        services.scan.scan(NOTES)
        # Read it, so the shared session is holding the file as it was.
        assert services.files.list_by_root(root.id)[0].size == len(CONTENT)
        (tree / INBOX).write_text(LONGER)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(services.scan.scan, NOTES).result()

        assert services.files.list_by_root(root.id)[0].size == len(LONGER)

    @staticmethod
    def test_a_root_that_is_not_there_still_raises(services, tmp_path):
        services.roots.sync({NOTES: tmp_path / "gone"})

        with (
            ThreadPoolExecutor(max_workers=1) as pool,
            pytest.raises(RootUnavailableError),
        ):
            pool.submit(services.scan.scan, NOTES).result()
