"""Integration tests for the files screen, over a real database.

The files screen is pushed on top of the roots screen, so every query here
goes through ``pilot.app.screen`` — ``pilot.app.query`` resolves against the
default screen and would never see it.
"""

from pathlib import Path

import pytest
from textual.widgets import DataTable, Static

from acervus.gates.tui.textual.files import LOOKAHEAD, PAGE

DOCS = "docs"
PHOTOS = "photos"
INBOX = "inbox.md"
HOLIDAY = "holiday"
SNAP = f"{HOLIDAY}/snap.txt"
YEAR = "2024"
DEEPER = f"{HOLIDAY}/{YEAR}/older.txt"
FOLDER = f"{HOLIDAY}/"  # how the table names a directory
CONTENT = "hello"
FILES_KEY = "f"
ROOT_KEY = "r"
OPEN_KEY = "enter"
UP_KEY = "backspace"
BACK_KEY = "escape"
SELECT_KEY = "space"
DOWN_KEY = "down"
END_KEY = "ctrl+end"
ADD_KEY = "a"
REMOVE_KEY = "x"
SUBMIT_KEY = "enter"
INVOICE = "invoice"
MARK_FILTER_KEY = "k"
STACK_KEY = "s"
UNSTACK_KEY = "u"
STACK_FILTER_KEY = "c"
TRIP = "trip"
NO_MATCHES_MESSAGE = "No files match this filter"
UP_ARROW = "up"
NO_ROOTS_MESSAGE = "No roots configured"
NO_FILES_MESSAGE = "No files indexed"
UP = ".."
BENEATH_HOLIDAY = "2"  # snap.txt and older.txt, counted on the directory's row
NOTHING = ""
PICKED = "•"
UNPICKED = " "
PICKED_BOTH = "2 selected"  # what the status says with both indexed files picked
PARTLY_DONE = f"{INVOICE}: 1 of 2 files."  # one of the two selected carried it
# The files table reads: selection mark, name, files beneath, size.
PICK_CELL = 0
NAME_CELL = 1
FILES_CELL = 2
SIZE_CELL = 3
OVER_A_PAGE = PAGE + LOOKAHEAD + 1  # far enough past the first page to reach for more


@pytest.fixture(name="trees")
def trees_fixture(*, tmp_path):
    docs = tmp_path / "docs"
    photos = tmp_path / "photos"
    for tree, relative_path in ((docs, INBOX), (photos, SNAP)):
        target = tree / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(CONTENT)
    return {DOCS: docs, PHOTOS: photos}


# One root holding a file at its top, a directory, and a directory below that.
@pytest.fixture(name="nested")
def nested_fixture(*, services, tmp_path):
    tree = tmp_path / DOCS
    for relative in (INBOX, SNAP, DEEPER):
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(CONTENT)
    services.roots.sync({DOCS: tree})
    services.scan.scan(DOCS)
    return services


# More files than one page holds, written to the index rather than to disk:
# what paging does is a property of the listing, not of the files behind it.
@pytest.fixture(name="crowded")
def crowded_fixture(*, services, repositories, tmp_path):
    services.roots.sync({DOCS: tmp_path / DOCS})
    root = services.roots.list_all()[0]
    with repositories.transaction.atomic():
        repositories.files.upsert_many(
            [
                {
                    "root_id": root.id,
                    "relative_path": Path(f"{index:04d}.txt"),
                    "size": 0,
                    "mtime": 0.0,
                }
                for index in range(OVER_A_PAGE)
            ]
        )
    return services


def index(services, trees) -> None:
    services.roots.sync(trees)
    for alias in trees:
        services.scan.scan(alias)


async def type_name(pilot, name) -> None:
    await pilot.press(*name, SUBMIT_KEY)


class TestFilesScreen:
    @staticmethod
    async def test_it_opens_in_the_first_root(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1  # the one file docs holds, and no more
            assert DOCS in str(label.render())

    @staticmethod
    async def test_a_row_names_the_file(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[NAME_CELL] == INBOX

    @staticmethod
    async def test_a_row_carries_the_size(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[SIZE_CELL] == str(len(CONTENT))

    @staticmethod
    async def test_an_empty_index_says_so(*, app, services, trees):
        services.roots.sync(trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            message = pilot.app.screen.query_one("#no-files", Static)

            assert message.display
            assert NO_FILES_MESSAGE in str(message.render())

    @staticmethod
    async def test_an_empty_index_hides_the_table(*, app, services, trees):
        services.roots.sync(trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)

            assert not pilot.app.screen.query_one("#files", DataTable).display

    @staticmethod
    async def test_the_root_key_steps_to_the_next_root(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ROOT_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert PHOTOS in str(label.render())
            assert table.get_row_at(0)[NAME_CELL] == FOLDER  # photos/holiday/

    @staticmethod
    async def test_the_root_key_wraps_back_round(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ROOT_KEY, ROOT_KEY)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert DOCS in str(label.render())

    @staticmethod
    async def test_the_root_key_stays_put_when_no_root_is_indexed(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ROOT_KEY)
            message = pilot.app.screen.query_one("#no-files", Static)

            assert NO_ROOTS_MESSAGE in str(message.render())

    @staticmethod
    async def test_back_returns_to_the_roots(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            await pilot.press(BACK_KEY)
            await pilot.pause()

            assert pilot.app.screen.query("#roots")
            assert not pilot.app.screen.query("#files")


class TestBrowsingDirectories:
    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_a_directory_is_a_row_of_its_own(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            # The directory first, then the root's own file, and nothing from
            # inside the directory.
            assert table.row_count == 1 + 1
            assert table.get_row_at(0)[NAME_CELL] == FOLDER
            assert table.get_row_at(1)[NAME_CELL] == INBOX

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_a_directory_counts_everything_beneath_it(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[FILES_CELL] == BENEATH_HOLIDAY
            assert table.get_row_at(1)[FILES_CELL] == NOTHING  # a file counts none

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_enter_opens_the_directory_under_the_cursor(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, OPEN_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert [
                table.get_row_at(row)[NAME_CELL] for row in range(table.row_count)
            ] == [UP, f"{YEAR}/", Path(SNAP).name]
            assert HOLIDAY in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_backspace_goes_back_up_to_where_it_came_from(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, OPEN_KEY, UP_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == 1 + 1  # the directory and the root's file
            assert table.cursor_row == 0  # back on the directory it came out of

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_enter_on_the_way_up_row_goes_up_too(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, OPEN_KEY, OPEN_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[NAME_CELL] == FOLDER

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_it_goes_no_further_up_than_the_root(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, UP_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[NAME_CELL] == FOLDER  # still at the top

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_enter_on_a_file_opens_nothing(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, DOWN_KEY, OPEN_KEY)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert HOLIDAY not in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_a_directory_cannot_be_marked(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await pilot.pause()

            assert not pilot.app.screen.query("#prompt")

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_a_directory_cannot_be_selected(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            status = pilot.app.screen.query_one("#status", Static)

            assert table.get_row_at(0)[PICK_CELL] == UNPICKED
            assert not str(status.render())

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_a_mark_filter_hides_a_directory_holding_no_match(*, app):
        async with app.run_test() as pilot:
            # The mark goes on the root's own file, so nothing under the
            # directory carries it.
            await pilot.press(FILES_KEY, DOWN_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(MARK_FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == 1
            assert table.get_row_at(0)[NAME_CELL] == INBOX

    @staticmethod
    @pytest.mark.usefixtures("nested")
    async def test_opening_a_directory_lets_the_selection_go(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, DOWN_KEY, SELECT_KEY)
            await pilot.press(UP_ARROW, OPEN_KEY, UP_KEY, DOWN_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(1)[PICK_CELL] == UNPICKED


class TestAChangeThatMovesAFileOutOfTheFilter:
    """A narrowed listing is read again when what it narrows by changes.

    The mark and the stack are two of the three things the listing is narrowed
    by, so putting one on or taking one off can move a file out of what is
    being shown. The rows would otherwise go on showing it until something
    else happened to redraw them.
    """

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_taking_the_filtered_mark_off_takes_the_row_off(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(MARK_FILTER_KEY)
            assert pilot.app.screen.query_one("#files", DataTable).row_count == 1

            await pilot.press(REMOVE_KEY)
            await type_name(pilot, INVOICE)

            assert pilot.app.screen.query_one("#files", DataTable).row_count == 0

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_emptied_listing_says_the_filter_matched_nothing(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(MARK_FILTER_KEY, REMOVE_KEY)
            await type_name(pilot, INVOICE)
            empty = pilot.app.screen.query_one("#no-files", Static)

            assert empty.display
            assert NO_MATCHES_MESSAGE in str(empty.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_taking_a_file_out_of_the_filtered_stack_takes_the_row_off(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, STACK_KEY)
            await type_name(pilot, TRIP)
            await pilot.press(STACK_FILTER_KEY)
            assert pilot.app.screen.query_one("#files", DataTable).row_count == 1

            # The one operation that asks for no name, so it takes its own way.
            await pilot.press(UNSTACK_KEY)

            assert pilot.app.screen.query_one("#files", DataTable).row_count == 0

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_an_unnarrowed_listing_is_left_where_it_was(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, DOWN_KEY, STACK_KEY)
            await type_name(pilot, TRIP)
            await pilot.press(UNSTACK_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == 1 + 1  # inbox.md and notes.md, both still shown
            assert table.cursor_row == 1  # and the cursor did not go back to the top

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_a_refused_change_leaves_the_rows_alone(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(MARK_FILTER_KEY, DOWN_KEY)

            # Nothing carries this one, so taking it off is refused outright.
            await pilot.press(REMOVE_KEY)
            await type_name(pilot, TRIP)

            assert pilot.app.screen.query_one("#files", DataTable).row_count == 1


class TestSelectingFiles:
    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_space_picks_the_file_under_the_cursor(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[PICK_CELL] == PICKED

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_space_again_lets_it_go(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY, SELECT_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[PICK_CELL] == UNPICKED

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_says_how_many_are_picked(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY, DOWN_KEY, SELECT_KEY)
            status = pilot.app.screen.query_one("#status", Static)

            assert PICKED_BOTH in str(status.render())

    @staticmethod
    async def test_a_mark_reaches_every_picked_file(*, app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY, DOWN_KEY, SELECT_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)

        carried = [
            mark.name
            for file in indexed.files.list_all()
            for mark in indexed.marks.list_for_file(file.id)
        ]
        assert carried == [INVOICE, INVOICE]  # both files

    @staticmethod
    async def test_a_mark_reaches_a_picked_file_the_cursor_has_left(*, app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY, DOWN_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)

        first, second = indexed.files.list_all()
        assert [mark.name for mark in indexed.marks.list_for_file(first.id)] == [
            INVOICE
        ]
        assert indexed.marks.list_for_file(second.id) == []

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_reports_how_many_it_reached(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY, DOWN_KEY, SELECT_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            status = pilot.app.screen.query_one("#status", Static)

            assert f"Marked 2 files {INVOICE}" in str(status.render())

    @staticmethod
    async def test_a_refusal_over_one_file_leaves_the_rest_done(*, app, indexed):
        async with app.run_test() as pilot:
            # Only the first file carries the mark, so taking it off both is
            # refused for the second — the mark is gone by the time it is asked.
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(SELECT_KEY, DOWN_KEY, SELECT_KEY, REMOVE_KEY)
            await type_name(pilot, INVOICE)
            status = pilot.app.screen.query_one("#status", Static)

            assert PARTLY_DONE in str(status.render())

        assert indexed.marks.list_all() == []  # it reached the file carrying it

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_a_filter_step_lets_the_selection_go(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, SELECT_KEY, MARK_FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[PICK_CELL] == UNPICKED


class TestReadingTheListingAPageAtATime:
    @staticmethod
    # The fixture indexes more files than one page holds.
    @pytest.mark.usefixtures("crowded")
    async def test_it_shows_a_page_before_reading_the_rest(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == PAGE

    @staticmethod
    @pytest.mark.usefixtures("crowded")
    async def test_the_cursor_nearing_the_end_reads_the_next_page(*, app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, END_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == OVER_A_PAGE

    @staticmethod
    async def test_a_file_on_a_later_page_can_be_marked(*, app, crowded):
        async with app.run_test() as pilot:
            # The first jump ends on the last row read so far, which is what
            # reads the rest; the second reaches the end of the whole listing.
            await pilot.press(FILES_KEY, END_KEY, END_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)

        last = crowded.files.list_all()[-1]
        assert [mark.name for mark in crowded.marks.list_for_file(last.id)] == [INVOICE]
