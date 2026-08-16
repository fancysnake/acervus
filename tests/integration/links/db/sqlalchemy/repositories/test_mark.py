"""Tests for the mark repository in links, against a real database."""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import MarkRepository
from acervus.pacts.mark import MarkDTO, MarkNotFoundError, MarkSummary

DOCS = "docs"
DOCS_PATH = Path("/home/user/docs")
TODO = Path("notes/todo.md")
INBOX = Path("notes/inbox.md")
UNKNOWN_ID = 404
INVOICE = "invoice"
HOLIDAY = "holiday"


class TestMarkRepository:
    @staticmethod
    def test_create_returns_a_dto_with_an_id(*, marks):
        mark = marks.create(INVOICE)

        assert isinstance(mark, MarkDTO)
        assert mark.name == INVOICE
        assert mark.id

    @staticmethod
    def test_read_by_name(*, marks):
        created = marks.create(INVOICE)

        assert marks.read_by_name(INVOICE).id == created.id

    @staticmethod
    def test_read_by_name_missing_raises(*, marks):
        with pytest.raises(MarkNotFoundError):
            marks.read_by_name(HOLIDAY)

    @staticmethod
    def test_list_all_is_empty_before_any_write(*, marks):
        assert marks.list_all() == []

    @staticmethod
    def test_list_all_counts_a_mark_nothing_carries_as_zero(*, marks):
        marks.create(INVOICE)

        assert marks.list_all() == [MarkSummary(id=1, name=INVOICE, file_count=0)]

    @staticmethod
    def test_list_all_is_ordered_by_name(*, marks):
        marks.create(INVOICE)
        marks.create(HOLIDAY)

        assert [mark.name for mark in marks.list_all()] == [HOLIDAY, INVOICE]

    @staticmethod
    def test_attach_puts_a_mark_on_a_file(*, marked_file, marks):
        mark = marks.create(INVOICE)

        marks.attach(marked_file.id, mark_id=mark.id)

        assert [found.name for found in marks.list_for_file(marked_file.id)] == [
            INVOICE
        ]

    @staticmethod
    def test_attaching_twice_links_once(*, marked_file, marks):
        mark = marks.create(INVOICE)

        marks.attach(marked_file.id, mark_id=mark.id)
        marks.attach(marked_file.id, mark_id=mark.id)

        assert marks.count_files(mark.id) == 1

    @staticmethod
    def test_list_for_file_is_ordered_by_name(*, marked_file, marks):
        for name in (INVOICE, HOLIDAY):
            marks.attach(marked_file.id, mark_id=marks.create(name).id)

        assert [found.name for found in marks.list_for_file(marked_file.id)] == [
            HOLIDAY,
            INVOICE,
        ]

    @staticmethod
    def test_list_for_file_is_empty_for_an_unmarked_file(*, marked_file, marks):
        marks.create(INVOICE)

        assert marks.list_for_file(marked_file.id) == []

    @staticmethod
    def test_a_mark_can_span_two_files(*, a_file, roots, files, marks):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        first, second = files.upsert_many(
            [a_file(root.id, TODO), a_file(root.id, INBOX)]
        )
        mark = marks.create(INVOICE)

        marks.attach(first.id, mark_id=mark.id)
        marks.attach(second.id, mark_id=mark.id)

        assert marks.count_files(mark.id) == 1 + 1  # both files carry it
        assert marks.list_all()[0].file_count == 1 + 1  # and the summary agrees

    @staticmethod
    def test_detach_takes_the_mark_off(*, marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark_id=mark.id)

        marks.detach(marked_file.id, mark_id=mark.id)

        assert marks.list_for_file(marked_file.id) == []
        assert marks.count_files(mark.id) == 0

    @staticmethod
    def test_detaching_a_mark_that_is_not_there_is_harmless(*, marked_file, marks):
        mark = marks.create(INVOICE)

        marks.detach(marked_file.id, mark_id=mark.id)

        assert marks.count_files(mark.id) == 0

    @staticmethod
    def test_detach_leaves_the_mark_itself(*, marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark_id=mark.id)

        marks.detach(marked_file.id, mark_id=mark.id)

        assert marks.read_by_name(INVOICE).id == mark.id

    @staticmethod
    def test_delete_removes_the_mark_and_its_links(*, marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark_id=mark.id)

        marks.delete(mark.id)

        assert marks.list_all() == []
        assert marks.list_for_file(marked_file.id) == []

    @staticmethod
    def test_deleting_an_unknown_mark_is_harmless(*, marks):
        marks.delete(UNKNOWN_ID)

        assert marks.list_all() == []

    @staticmethod
    def test_count_files_is_zero_for_an_unknown_mark(*, marks):
        assert marks.count_files(UNKNOWN_ID) == 0

    @staticmethod
    def test_marks_reach_the_database_file(*, engine, session, marked_file, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark_id=mark.id)
        session.commit()

        with Session(engine) as fresh:
            reopened = MarkRepository(fresh).list_all()

        assert reopened == [MarkSummary(id=mark.id, name=INVOICE, file_count=1)]
