"""Tests for the file repository in links, against a real database."""

from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from acervus.links.db.sqlalchemy.models import FileMark
from acervus.links.db.sqlalchemy.repositories.file import BATCH
from acervus.pacts.file import BARE, FileDTO, FileFilter

DOCS = "docs"
PHOTOS = "photos"
DOCS_PATH = Path("/home/user/docs")
PHOTOS_PATH = Path("/home/user/photos")
TODO = Path("notes/todo.md")
INBOX = Path("notes/inbox.md")
OTHER_SIZE = 34
GROWN_SIZE = 99
LATER_MTIME = 2.5
UNKNOWN_ID = 404
INVOICE = "invoice"
HOLIDAY = "holiday"
TRIP = "iceland trip"
SPANNING = BATCH * 2 + 1  # two full statements and a remainder
PAGE = 2  # a page narrower than the listing, so where it cuts is visible
PAGED = PAGE * 2 + 1  # two full pages and a remainder


def _numbered_paths(count: int) -> list[Path]:
    """Return that many paths, named so they sort the way they are built.

    Returns:
        Paths in the order the listing returns them, so order is assertable.
    """
    return [Path(f"notes/{index:04d}.md") for index in range(count)]


def _spanning_paths() -> list[Path]:
    """Return more paths than one statement can bind parameters for.

    Returns:
        Paths that sort the way they are built, so order is assertable.
    """
    return _numbered_paths(SPANNING)


class TestFileRepository:
    @staticmethod
    def test_upsert_many_inserts(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]

        written = files.upsert_many(
            [a_file(root.id, TODO), a_file(root.id, INBOX, size=OTHER_SIZE)]
        )

        assert len(written) == 1 + 1  # two files under one root
        assert isinstance(written[0], FileDTO)
        assert {file.relative_path for file in written} == {TODO, INBOX}

    # Scanning a root holding no files writes nothing, so the empty write is
    # reachable.
    @staticmethod
    def test_upsert_many_writes_nothing_when_given_nothing(*, files):
        assert files.upsert_many([]) == []
        assert files.list_all() == []

    @staticmethod
    def test_upsert_many_updates_size_and_mtime(*, a_file, roots, files):
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
    def test_the_same_relative_path_under_two_roots_stays_distinct(
        *, a_file, roots, files
    ):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )

        files.upsert_many(
            [a_file(docs.id, TODO), a_file(photos.id, TODO, size=OTHER_SIZE)]
        )

        assert len(files.list_by_root(docs.id)) == 1
        assert files.list_by_root(photos.id)[0].size == OTHER_SIZE

    @staticmethod
    def test_list_by_root_is_ordered_by_relative_path(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])

        listed = files.list_by_root(root.id)

        assert [file.relative_path for file in listed] == [INBOX, TODO]

    @staticmethod
    def test_list_by_root_is_empty_for_an_unknown_root(*, files):
        assert files.list_by_root(UNKNOWN_ID) == []

    @staticmethod
    def test_list_all_spans_every_root(*, a_file, roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        files.upsert_many([a_file(docs.id, TODO), a_file(photos.id, INBOX)])

        assert len(files.list_all()) == 1 + 1  # one file under each root

    @staticmethod
    def test_list_all_narrows_to_one_root(*, a_file, roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        files.upsert_many([a_file(docs.id, TODO), a_file(photos.id, INBOX)])

        listed = files.list_all(FileFilter(root_id=photos.id))

        assert [file.relative_path for file in listed] == [INBOX]

    @staticmethod
    def test_list_all_is_ordered_by_root_then_path(*, a_file, roots, files):
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
    def test_list_all_is_empty_before_any_write(*, files):
        assert files.list_all() == []

    @staticmethod
    def test_list_all_reads_at_most_a_page(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, path) for path in _numbered_paths(PAGED)])

        assert len(files.list_all(limit=PAGE)) == PAGE

    @staticmethod
    def test_list_all_takes_the_page_at_the_offset(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        paths = _numbered_paths(PAGED)
        files.upsert_many([a_file(root.id, path) for path in paths])

        listed = files.list_all(limit=PAGE, offset=PAGE)

        assert [file.relative_path for file in listed] == paths[PAGE : PAGE + PAGE]

    @staticmethod
    def test_list_all_reads_nothing_past_the_end(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, path) for path in _numbered_paths(PAGE)])

        assert files.list_all(limit=PAGE, offset=PAGE) == []

    @staticmethod
    def test_list_all_pages_within_the_filter(*, a_file, roots, files):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        files.upsert_many(
            [a_file(docs.id, path) for path in _numbered_paths(PAGED)]
            + [a_file(photos.id, INBOX)]
        )

        listed = files.list_all(FileFilter(root_id=photos.id), limit=PAGE)

        assert [file.relative_path for file in listed] == [INBOX]

    @staticmethod
    def test_delete_many(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        written = files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])

        files.delete_many([written[0].id])

        remaining = files.list_by_root(root.id)
        assert len(remaining) == 1
        assert remaining[0].id == written[1].id

    @staticmethod
    def test_delete_many_takes_the_marks_off_with_it(*, marked_file, files, marks):
        mark = marks.create(INVOICE)
        marks.attach(marked_file.id, mark_id=mark.id)

        files.delete_many([marked_file.id])

        assert marks.count_files(mark.id) == 0


# The schema declares every cascade, so these hold however the rows are
# deleted — a bulk statement included.


class TestTheDatabaseEnforcesIt:
    @staticmethod
    def test_a_file_needs_a_root_that_exists(*, a_file, files):
        with pytest.raises(IntegrityError):
            files.upsert_many([a_file(UNKNOWN_ID, TODO)])

    @staticmethod
    def test_a_link_needs_a_mark_that_exists(*, marked_file, session):
        session.add(FileMark(file_id=marked_file.id, mark_id=UNKNOWN_ID))

        with pytest.raises(IntegrityError):
            session.flush()

    @staticmethod
    def test_dropping_a_root_leaves_no_file_behind(*, a_file, roots, files, marks):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        written = files.upsert_many([a_file(root.id, TODO)])[0]
        mark = marks.create(INVOICE)
        marks.attach(written.id, mark_id=mark.id)

        roots.delete_many([DOCS])

        assert files.list_all() == []
        assert marks.count_files(mark.id) == 0


class TestFileRepositoryMarkFilter:
    @staticmethod
    def test_it_keeps_only_files_carrying_the_mark(*, a_file, roots, files, marks):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        todo, _ = files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])
        invoice = marks.create(INVOICE)
        marks.attach(todo.id, mark_id=invoice.id)

        listed = files.list_all(FileFilter(mark_id=invoice.id))

        assert [file.relative_path for file in listed] == [TODO]

    @staticmethod
    def test_an_unused_mark_matches_nothing(*, a_file, roots, files, marks):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        files.upsert_many([a_file(root.id, TODO)])
        invoice = marks.create(INVOICE)

        assert files.list_all(FileFilter(mark_id=invoice.id)) == []

    @staticmethod
    def test_a_file_is_listed_once_however_many_marks_it_carries(
        *, a_file, roots, files, marks
    ):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        todo = files.upsert_many([a_file(root.id, TODO)])[0]
        invoice = marks.create(INVOICE)
        for mark in (invoice, marks.create(HOLIDAY)):
            marks.attach(todo.id, mark_id=mark.id)

        assert len(files.list_all(FileFilter(mark_id=invoice.id))) == 1

    @staticmethod
    def test_unmarked_keeps_only_files_carrying_nothing(*, a_file, roots, files, marks):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        todo, _ = files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])
        marks.attach(todo.id, mark_id=marks.create(INVOICE).id)

        listed = files.list_all(FileFilter(mark_id=BARE))

        assert [file.relative_path for file in listed] == [INBOX]

    @staticmethod
    def test_a_file_stripped_of_its_marks_counts_as_unmarked(
        *, a_file, roots, files, marks
    ):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        todo = files.upsert_many([a_file(root.id, TODO)])[0]
        mark = marks.create(INVOICE)
        marks.attach(todo.id, mark_id=mark.id)

        marks.detach(todo.id, mark_id=mark.id)

        assert len(files.list_all(FileFilter(mark_id=BARE))) == 1

    @staticmethod
    def test_the_root_and_mark_filters_combine(*, a_file, roots, files, marks):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        here, there = files.upsert_many(
            [a_file(docs.id, TODO), a_file(photos.id, TODO)]
        )
        mark = marks.create(INVOICE)
        marks.attach(here.id, mark_id=mark.id)
        marks.attach(there.id, mark_id=mark.id)

        listed = files.list_all(FileFilter(root_id=docs.id, mark_id=mark.id))

        assert [file.root_id for file in listed] == [docs.id]


class TestFileRepositoryStackFilter:
    @staticmethod
    def test_it_keeps_only_files_sitting_in_the_stack(*, two_files, files, stacks):
        todo, _ = two_files
        trip = stacks.create(TRIP)
        stacks.set_for_file(todo.id, stack_id=trip.id)

        listed = files.list_all(FileFilter(stack_id=trip.id))

        assert [file.relative_path for file in listed] == [TODO]

    @staticmethod
    @pytest.mark.usefixtures("two_files")
    def test_an_empty_stack_matches_nothing(*, files, stacks):
        trip = stacks.create(TRIP)

        assert files.list_all(FileFilter(stack_id=trip.id)) == []

    @staticmethod
    def test_unstacked_keeps_only_files_sitting_in_none(*, two_files, files, stacks):
        todo, _ = two_files
        stacks.set_for_file(todo.id, stack_id=stacks.create(TRIP).id)

        listed = files.list_all(FileFilter(stack_id=BARE))

        assert [file.relative_path for file in listed] == [INBOX]

    @staticmethod
    def test_a_file_taken_out_counts_as_unstacked(*, two_files, files, stacks):
        todo, _ = two_files
        stacks.set_for_file(todo.id, stack_id=stacks.create(TRIP).id)

        stacks.set_for_file(todo.id, stack_id=None)

        assert len(files.list_all(FileFilter(stack_id=BARE))) == 1 + 1  # both loose

    @staticmethod
    def test_the_root_and_stack_filters_combine(*, a_file, roots, files, stacks):
        docs, photos = roots.upsert_many(
            [{"alias": DOCS, "path": DOCS_PATH}, {"alias": PHOTOS, "path": PHOTOS_PATH}]
        )
        here, there = files.upsert_many(
            [a_file(docs.id, TODO), a_file(photos.id, TODO)]
        )
        trip = stacks.create(TRIP)
        stacks.set_for_file(here.id, stack_id=trip.id)
        stacks.set_for_file(there.id, stack_id=trip.id)

        listed = files.list_all(FileFilter(root_id=docs.id, stack_id=trip.id))

        assert [file.root_id for file in listed] == [docs.id]

    @staticmethod
    def test_a_stack_and_a_mark_narrow_together(*, two_files, files, marks, stacks):
        todo, inbox = two_files
        trip = stacks.create(TRIP)
        invoice = marks.create(INVOICE)
        stacks.set_for_file(todo.id, stack_id=trip.id)
        stacks.set_for_file(inbox.id, stack_id=trip.id)
        marks.attach(todo.id, mark_id=invoice.id)

        listed = files.list_all(FileFilter(stack_id=trip.id, mark_id=invoice.id))

        assert [file.relative_path for file in listed] == [TODO]


# A scan of a real root hands over far more files than SQLite will bind
# parameters for in one statement, so each of these writes spans several.
class TestWritingMoreFilesThanOneStatementHolds:
    @staticmethod
    def test_upsert_many_writes_every_batch(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]

        written = files.upsert_many(
            [a_file(root.id, path) for path in _spanning_paths()]
        )

        assert len(written) == SPANNING
        assert len(files.list_by_root(root.id)) == SPANNING

    @staticmethod
    def test_upsert_many_keeps_the_order_it_was_given(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        paths = list(reversed(_spanning_paths()))

        written = files.upsert_many([a_file(root.id, path) for path in paths])

        assert [file.relative_path for file in written] == paths

    @staticmethod
    def test_upsert_many_updates_across_batches(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        paths = _spanning_paths()
        files.upsert_many([a_file(root.id, path) for path in paths])

        rewritten = files.upsert_many(
            [a_file(root.id, path, size=GROWN_SIZE) for path in paths]
        )

        assert {file.size for file in rewritten} == {GROWN_SIZE}
        assert len(files.list_by_root(root.id)) == SPANNING

    @staticmethod
    def test_delete_many_empties_every_batch(*, a_file, roots, files):
        root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
        written = files.upsert_many(
            [a_file(root.id, path) for path in _spanning_paths()]
        )

        files.delete_many([file.id for file in written])

        assert files.list_by_root(root.id) == []
