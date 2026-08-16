"""Tests for the SQLAlchemy transaction adapter, against a real database."""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import RootRepository, SessionTransaction

DOCS = "docs"
DOCS_PATH = Path("/home/user/docs")
PHOTOS = "photos"
PHOTOS_PATH = Path("/home/user/photos")
FAILURE = "the sync went wrong"


def aliases_on_disk(engine) -> list[str]:
    with Session(engine) as fresh:
        return [root.alias for root in RootRepository(fresh).list_all()]


def refuse_to_commit() -> None:
    """Stand in for a commit that fails on the way to disk.

    Raises:
        RuntimeError: always, in place of committing.
    """
    raise RuntimeError(FAILURE)


class TestSessionTransaction:
    @staticmethod
    def test_a_clean_exit_commits(*, engine, session):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)

        with transaction.atomic():
            roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        assert aliases_on_disk(engine) == [DOCS]

    @staticmethod
    def test_an_exception_rolls_back(*, engine, session):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)

        def write_then_fail() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])
                raise RuntimeError(FAILURE)

        with pytest.raises(RuntimeError):
            write_then_fail()

        assert aliases_on_disk(engine) == []

    @staticmethod
    def test_an_exception_rolls_back_the_whole_block(*, engine, session):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)
        with transaction.atomic():
            roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        def write_then_delete_then_fail() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": PHOTOS, "path": PHOTOS_PATH}])
                roots.delete_many([DOCS])
                raise RuntimeError(FAILURE)

        with pytest.raises(RuntimeError):
            write_then_delete_then_fail()

        assert aliases_on_disk(engine) == [DOCS]

    @staticmethod
    def test_the_session_stays_usable_after_a_rollback(*, engine, session):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)

        def write_then_fail() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])
                raise RuntimeError(FAILURE)

        with pytest.raises(RuntimeError):
            write_then_fail()

        with transaction.atomic():
            roots.upsert_many([{"alias": PHOTOS, "path": PHOTOS_PATH}])

        assert aliases_on_disk(engine) == [PHOTOS]

    @staticmethod
    def test_an_interrupt_rolls_back(*, engine, session):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)

        def write_then_interrupt() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])
                raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            write_then_interrupt()

        assert aliases_on_disk(engine) == []

    @staticmethod
    def test_an_interrupted_write_never_reaches_a_later_block(*, engine, session):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)

        def write_then_interrupt() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])
                raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            write_then_interrupt()

        with transaction.atomic():
            roots.upsert_many([{"alias": PHOTOS, "path": PHOTOS_PATH}])

        assert aliases_on_disk(engine) == [PHOTOS]

    @staticmethod
    def test_a_failed_commit_rolls_back(*, engine, session, monkeypatch):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)
        monkeypatch.setattr(session, "commit", refuse_to_commit)

        def write_then_fail_to_commit() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        with pytest.raises(RuntimeError):
            write_then_fail_to_commit()

        monkeypatch.undo()

        assert aliases_on_disk(engine) == []

    @staticmethod
    def test_a_failed_commit_never_reaches_a_later_block(
        *, engine, session, monkeypatch
    ):
        transaction = SessionTransaction(session)
        roots = RootRepository(session)
        monkeypatch.setattr(session, "commit", refuse_to_commit)

        def write_then_fail_to_commit() -> None:
            with transaction.atomic():
                roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        with pytest.raises(RuntimeError):
            write_then_fail_to_commit()

        monkeypatch.undo()

        with transaction.atomic():
            roots.upsert_many([{"alias": PHOTOS, "path": PHOTOS_PATH}])

        assert aliases_on_disk(engine) == [PHOTOS]

    @staticmethod
    def test_an_empty_block_commits_nothing(*, engine, session):
        transaction = SessionTransaction(session)

        with transaction.atomic():
            pass

        assert aliases_on_disk(engine) == []
