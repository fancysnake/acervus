"""Tests for the root repository in links, against a real database."""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import RootRepository
from acervus.pacts.root import RootDTO, RootNotFoundError

DOCS = "docs"
PHOTOS = "photos"
MUSIC = "music"
DOCS_PATH = Path("/home/user/docs")
PHOTOS_PATH = Path("/home/user/photos")
MUSIC_PATH = Path("/home/user/music")
MOVED_PATH = Path("/mnt/archive/docs")
TODO = Path("notes/todo.md")


class TestRootRepository:
    @staticmethod
    def test_upsert_many_inserts(*, roots):
        written = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )

        assert len(written) == 1 + 1  # docs + photos
        assert {root.alias for root in written} == {DOCS, PHOTOS}
        assert all(root.id for root in written)

    @staticmethod
    def test_upsert_many_returns_dtos(*, roots):
        written = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        assert isinstance(written[0], RootDTO)
        assert written[0].path == DOCS_PATH

    # A config naming no roots syncs nothing, so the empty write is reachable.
    @staticmethod
    def test_upsert_many_writes_nothing_when_given_nothing(*, roots):
        assert roots.upsert_many([]) == []
        assert roots.list_all() == []

    @staticmethod
    def test_upsert_many_updates_an_existing_alias(*, roots):
        first = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        second = roots.upsert_many([{"alias": DOCS, "path": MOVED_PATH}])

        assert second[0].id == first[0].id
        assert second[0].path == MOVED_PATH
        assert len(roots.list_all()) == 1

    @staticmethod
    def test_list_all_is_ordered_by_alias(*, roots):
        roots.upsert_many(
            [
                {"alias": PHOTOS, "path": PHOTOS_PATH},
                {"alias": DOCS, "path": DOCS_PATH},
                {"alias": MUSIC, "path": MUSIC_PATH},
            ]
        )

        assert [root.alias for root in roots.list_all()] == [DOCS, MUSIC, PHOTOS]

    @staticmethod
    def test_list_all_is_empty_before_any_write(*, roots):
        assert roots.list_all() == []

    @staticmethod
    def test_read_by_alias(*, roots):
        roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        assert roots.read_by_alias(DOCS).path == DOCS_PATH

    @staticmethod
    def test_read_by_alias_missing_raises(*, roots):
        with pytest.raises(RootNotFoundError):
            roots.read_by_alias(MUSIC)

    @staticmethod
    def test_delete_many(*, roots):
        roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )

        roots.delete_many([DOCS])

        assert [root.alias for root in roots.list_all()] == [PHOTOS]

    @staticmethod
    def test_delete_many_ignores_unknown_aliases(*, roots):
        roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        roots.delete_many([MUSIC])

        assert len(roots.list_all()) == 1

    @staticmethod
    def test_delete_many_takes_the_files_with_it(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, TODO)])

        roots.delete_many([DOCS])

        assert files.list_by_root(root.id) == []

    @staticmethod
    def test_writes_reach_the_database_file(*, engine, session, roots):
        roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])
        session.commit()

        with Session(engine) as fresh:
            reopened = RootRepository(fresh).list_all()

        assert [root.alias for root in reopened] == [DOCS]
