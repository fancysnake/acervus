"""Tests for the containers in inits, against a real database."""

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

NOTES = "notes"
NOTES_PATH = Path("/home/user/notes")
ARCHIVE = "archive"
ARCHIVE_PATH = Path("/home/user/archive")


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
    def test_the_repositories_are_cached(repositories):
        assert repositories.roots is repositories.roots
        assert repositories.session is repositories.session


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
