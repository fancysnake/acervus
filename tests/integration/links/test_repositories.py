"""Tests for the SQLAlchemy repositories in links, against a real database."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import FileRepository, MarkRepository, RootRepository
from acervus.pacts.file import FileDTO, FileWrite
from acervus.pacts.mark import MarkDTO, MarkNotFoundError, MarkSummary
from acervus.pacts.root import RootDTO, RootNotFoundError

DOCS = "docs"
PHOTOS = "photos"
MUSIC = "music"
DOCS_PATH = Path("/home/user/docs")
PHOTOS_PATH = Path("/home/user/photos")
MUSIC_PATH = Path("/home/user/music")
MOVED_PATH = Path("/mnt/archive/docs")
TODO = Path("notes/todo.md")
INBOX = Path("notes/inbox.md")
SIZE = 12
OTHER_SIZE = 34
GROWN_SIZE = 99
MTIME = 1.5
LATER_MTIME = 2.5
UNKNOWN_ID = 404
INVOICE = "invoice"
HOLIDAY = "holiday"


# Builds one file write, so the tests below read as data rather than dict noise.
def a_file(root_id, relative_path, size=SIZE, mtime=MTIME) -> FileWrite:
    return {
        "root_id": root_id,
        "relative_path": relative_path,
        "size": size,
        "mtime": mtime,
    }


@pytest.fixture(name="roots")
def roots_fixture(session):
    return RootRepository(session)


@pytest.fixture(name="files")
def files_fixture(session):
    return FileRepository(session)


@pytest.fixture(name="marks")
def marks_fixture(session):
    return MarkRepository(session)


@pytest.fixture(name="marked_file")
def marked_file_fixture(roots, files):
    root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
    return files.upsert_many([a_file(root.id, TODO)])[0]


class TestRootRepository:
    @staticmethod
    def test_upsert_many_inserts(roots):
        written = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )

        assert len(written) == 1 + 1  # docs + photos
        assert {root.alias for root in written} == {DOCS, PHOTOS}
        assert all(root.id for root in written)

    @staticmethod
    def test_upsert_many_returns_dtos(roots):
        written = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        assert isinstance(written[0], RootDTO)
        assert written[0].path == DOCS_PATH

    @staticmethod
    def test_upsert_many_updates_an_existing_alias(roots):
        first = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        second = roots.upsert_many([{"alias": DOCS, "path": MOVED_PATH}])

        assert second[0].id == first[0].id
        assert second[0].path == MOVED_PATH
        assert len(roots.list_all()) == 1

    @staticmethod
    def test_list_all_is_ordered_by_alias(roots):
        roots.upsert_many(
            [
                {"alias": PHOTOS, "path": PHOTOS_PATH},
                {"alias": DOCS, "path": DOCS_PATH},
                {"alias": MUSIC, "path": MUSIC_PATH},
            ]
        )

        assert [root.alias for root in roots.list_all()] == [DOCS, MUSIC, PHOTOS]

    @staticmethod
    def test_list_all_is_empty_before_any_write(roots):
        assert roots.list_all() == []

    @staticmethod
    def test_read(roots):
        written = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        found = roots.read(written[0].id)

        assert found.alias == DOCS
        assert found.path == DOCS_PATH

    @staticmethod
    def test_read_missing_raises(roots):
        with pytest.raises(RootNotFoundError):
            roots.read(UNKNOWN_ID)

    @staticmethod
    def test_read_by_alias(roots):
        roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        assert roots.read_by_alias(DOCS).path == DOCS_PATH

    @staticmethod
    def test_read_by_alias_missing_raises(roots):
        with pytest.raises(RootNotFoundError):
            roots.read_by_alias(MUSIC)

    @staticmethod
    def test_delete_many(roots):
        roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )

        roots.delete_many([DOCS])

        assert [root.alias for root in roots.list_all()] == [PHOTOS]

    @staticmethod
    def test_delete_many_ignores_unknown_aliases(roots):
        roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])

        roots.delete_many([MUSIC])

        assert len(roots.list_all()) == 1

    @staticmethod
    def test_delete_many_takes_the_files_with_it(roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, TODO)])

        roots.delete_many([DOCS])

        assert files.list_by_root(root.id) == []

    @staticmethod
    def test_writes_reach_the_database_file(engine, session, roots):
        roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])
        session.commit()

        with Session(engine) as fresh:
            reopened = RootRepository(fresh).list_all()

        assert [root.alias for root in reopened] == [DOCS]


class TestFileRepository:
    @staticmethod
    def test_upsert_many_inserts(roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]

        written = files.upsert_many(
            [a_file(root.id, TODO), a_file(root.id, INBOX, size=OTHER_SIZE)]
        )

        assert len(written) == 1 + 1  # two files under one root
        assert isinstance(written[0], FileDTO)
        assert {file.relative_path for file in written} == {TODO, INBOX}

    @staticmethod
    def test_upsert_many_updates_size_and_mtime(roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        first = files.upsert_many([a_file(root.id, TODO)])

        second = files.upsert_many(
            [a_file(root.id, TODO, size=GROWN_SIZE, mtime=LATER_MTIME)]
        )

        assert second[0].id == first[0].id
        assert second[0].size == GROWN_SIZE
        assert second[0].mtime == pytest.approx(LATER_MTIME)
        assert len(files.list_by_root(root.id)) == 1

    @staticmethod
    def test_the_same_relative_path_under_two_roots_stays_distinct(roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )

        files.upsert_many(
            [a_file(docs.id, TODO), a_file(photos.id, TODO, size=OTHER_SIZE)]
        )

        assert len(files.list_by_root(docs.id)) == 1
        assert files.list_by_root(photos.id)[0].size == OTHER_SIZE

    @staticmethod
    def test_list_by_root_is_ordered_by_relative_path(roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])

        listed = files.list_by_root(root.id)

        assert [file.relative_path for file in listed] == [INBOX, TODO]

    @staticmethod
    def test_list_by_root_is_empty_for_an_unknown_root(files):
        assert files.list_by_root(UNKNOWN_ID) == []

    @staticmethod
    def test_list_all_spans_every_root(roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        files.upsert_many([a_file(docs.id, TODO), a_file(photos.id, INBOX)])

        assert len(files.list_all()) == 1 + 1  # one file under each root

    @staticmethod
    def test_list_all_narrows_to_one_root(roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        files.upsert_many([a_file(docs.id, TODO), a_file(photos.id, INBOX)])

        listed = files.list_all(photos.id)

        assert [file.relative_path for file in listed] == [INBOX]

    @staticmethod
    def test_list_all_is_ordered_by_root_then_path(roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        files.upsert_many(
            [a_file(photos.id, TODO), a_file(docs.id, TODO), a_file(docs.id, INBOX)]
        )

        listed = files.list_all()

        assert [(file.root_id, file.relative_path) for file in listed] == [
            (docs.id, INBOX),
            (docs.id, TODO),
            (photos.id, TODO),
        ]

    @staticmethod
    def test_list_all_is_empty_before_any_write(files):
        assert files.list_all() == []

    @staticmethod
    def test_delete_many(roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        written = files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])

        files.delete_many([written[0].id])

        remaining = files.list_by_root(root.id)
        assert len(remaining) == 1
        assert remaining[0].id == written[1].id


class TestMarkRepository:
    @staticmethod
    def test_create_returns_a_dto_with_an_id(marks):
        mark = marks.create(INVOICE)

        assert isinstance(mark, MarkDTO)
        assert mark.name == INVOICE
        assert mark.id

    @staticmethod
    def test_read_by_name(marks):
        created = marks.create(INVOICE)

        assert marks.read_by_name(INVOICE).id == created.id

    @staticmethod
    def test_read_by_name_missing_raises(marks):
        with pytest.raises(MarkNotFoundError):
            marks.read_by_name(HOLIDAY)

    @staticmethod
    def test_list_all_is_empty_before_any_write(marks):
        assert marks.list_all() == []

    @staticmethod
    def test_list_all_counts_a_mark_nothing_carries_as_zero(marks):
        marks.create(INVOICE)

        assert marks.list_all() == [MarkSummary(id=1, name=INVOICE, file_count=0)]

    @staticmethod
    def test_list_all_is_ordered_by_name(marks):
        marks.create(INVOICE)
        marks.create(HOLIDAY)

        assert [mark.name for mark in marks.list_all()] == [HOLIDAY, INVOICE]

    @staticmethod
    def test_attach_puts_a_mark_on_a_file(marked_file, marks):
        mark = marks.create(INVOICE)

        marks.attach(marked_file.id, mark.id)

        assert [found.name for found in marks.list_for_file(marked_file.id)] == [
            INVOICE
        ]

    @staticmethod
    def test_attaching_twice_links_once(marked_file, marks):
        mark = marks.create(INVOICE)

        marks.attach(marked_file.id, mark.id)
        marks.attach(marked_file.id, mark.id)

        assert marks.count_files(mark.id) == 1

    @staticmethod
    def test_list_for_file_is_ordered_by_name(marked_file, marks):
        for name in (INVOICE, HOLIDAY):
            marks.attach(marked_file.id, marks.create(name).id)

        assert [found.name for found in marks.list_for_file(marked_file.id)] == [
            HOLIDAY,
            INVOICE,
        ]

    @staticmethod
    def test_list_for_file_is_empty_for_an_unmarked_file(marked_file, marks):
        marks.create(INVOICE)

        assert marks.list_for_file(marked_file.id) == []

    @staticmethod
    def test_a_mark_can_span_two_files(roots, files, marks):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        first, second = files.upsert_many(
            [a_file(root.id, TODO), a_file(root.id, INBOX)]
        )
        mark = marks.create(INVOICE)

        marks.attach(first.id, mark.id)
        marks.attach(second.id, mark.id)

        assert marks.count_files(mark.id) == 1 + 1  # both files carry it
        assert marks.list_all()[0].file_count == 1 + 1  # and the summary agrees

    @staticmethod
    def test_detach_takes_the_mark_off(marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark.id)

        marks.detach(marked_file.id, mark.id)

        assert marks.list_for_file(marked_file.id) == []
        assert marks.count_files(mark.id) == 0

    @staticmethod
    def test_detaching_a_mark_that_is_not_there_is_harmless(marked_file, marks):
        mark = marks.create(INVOICE)

        marks.detach(marked_file.id, mark.id)

        assert marks.count_files(mark.id) == 0

    @staticmethod
    def test_detach_leaves_the_mark_itself(marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark.id)

        marks.detach(marked_file.id, mark.id)

        assert marks.read_by_name(INVOICE).id == mark.id

    @staticmethod
    def test_delete_removes_the_mark_and_its_links(marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark.id)

        marks.delete(mark.id)

        assert marks.list_all() == []
        assert marks.list_for_file(marked_file.id) == []

    @staticmethod
    def test_deleting_an_unknown_mark_is_harmless(marks):
        marks.delete(UNKNOWN_ID)

        assert marks.list_all() == []

    @staticmethod
    def test_count_files_is_zero_for_an_unknown_mark(marks):
        assert marks.count_files(UNKNOWN_ID) == 0

    @staticmethod
    def test_marks_reach_the_database_file(engine, session, marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark.id)
        session.commit()

        with Session(engine) as fresh:
            reopened = MarkRepository(fresh).list_all()

        assert reopened == [MarkSummary(id=mark.id, name=INVOICE, file_count=1)]
