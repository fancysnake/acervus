"""Integration tests for marking files from the TUI, over a real database.

Marks are put on files from the files screen and listed on the marks screen,
both of which are pushed, so queries go through ``pilot.app.screen``.
"""

import pytest
from textual.widgets import DataTable, Static

INBOX = "inbox.md"
NOTES = "notes.md"
INVOICE = "invoice"
HOLIDAY = "holiday"
FILES_KEY = "f"
MARKS_KEY = "m"
ADD_KEY = "a"
REMOVE_KEY = "x"
BACK_KEY = "escape"
DOWN_KEY = "down"
SUBMIT_KEY = "enter"
NO_MARKS_MESSAGE = "No marks yet"
NO_MARKS_CARRIED = "Marks: none"
REJECTED = "cannot contain"
BAD_NAME = "no:colons"
MARK_FILTER_KEY = "k"
ANY_MARK = "any mark"
UNMARKED = "unmarked"
NO_MATCHES_MESSAGE = "No files match this filter"


async def type_name(pilot, name: str) -> None:
    await pilot.press(*name, SUBMIT_KEY)


async def open_files_and_mark_first(pilot) -> None:
    """Open the files screen and put INVOICE on the first file, inbox.md."""
    await pilot.press(FILES_KEY, ADD_KEY)
    await type_name(pilot, INVOICE)


class TestAddingAMark:
    @staticmethod
    async def test_it_reaches_the_index(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)

        assert [mark.name for mark in indexed.marks.list_all()] == [INVOICE]

    @staticmethod
    async def test_it_lands_on_the_file_under_the_cursor(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)

        first = indexed.files.list_all()[0]
        assert [mark.name for mark in indexed.marks.list_for_file(first.id)] == [
            INVOICE
        ]

    @staticmethod
    async def test_it_follows_the_cursor(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, DOWN_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)

        first, second = indexed.files.list_all()
        assert indexed.marks.list_for_file(first.id) == []
        assert [mark.name for mark in indexed.marks.list_for_file(second.id)] == [
            INVOICE
        ]

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_screen_reports_it(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            status = pilot.app.screen.query_one("#mark-status", Static)

            assert INVOICE in str(status.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_screen_shows_what_the_file_carries(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            carried = pilot.app.screen.query_one("#file-marks", Static)

            assert INVOICE in str(carried.render())

    @staticmethod
    async def test_two_marks_on_one_file(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(ADD_KEY)
            await type_name(pilot, HOLIDAY)

        first = indexed.files.list_all()[0]
        assert [mark.name for mark in indexed.marks.list_for_file(first.id)] == [
            HOLIDAY,
            INVOICE,
        ]

    @staticmethod
    async def test_backing_out_of_the_prompt_marks_nothing(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await pilot.press(*INVOICE, BACK_KEY)

        assert indexed.marks.list_all() == []

    @staticmethod
    async def test_a_bad_name_is_reported_and_not_stored(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, BAD_NAME)
            status = pilot.app.screen.query_one("#mark-status", Static)

            assert REJECTED in str(status.render())

        assert indexed.marks.list_all() == []


class TestRemovingAMark:
    @staticmethod
    async def test_it_leaves_the_index(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(REMOVE_KEY)
            await type_name(pilot, INVOICE)

        assert indexed.marks.list_all() == []

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_screen_reports_it(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(REMOVE_KEY)
            await type_name(pilot, INVOICE)
            carried = pilot.app.screen.query_one("#file-marks", Static)

            assert NO_MARKS_CARRIED in str(carried.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_an_unknown_mark_is_reported(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, REMOVE_KEY)
            await type_name(pilot, HOLIDAY)
            status = pilot.app.screen.query_one("#mark-status", Static)

            assert HOLIDAY in str(status.render())

    @staticmethod
    async def test_a_mark_another_file_still_carries_survives(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(DOWN_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(REMOVE_KEY)
            await type_name(pilot, INVOICE)

        assert [mark.name for mark in indexed.marks.list_all()] == [INVOICE]


class TestFilteringByMark:
    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_starts_showing_any_mark(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert ANY_MARK in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_narrows_to_files_carrying_the_mark(app):
        async with app.run_test() as pilot:
            await open_files_and_mark_first(pilot)
            await pilot.press(MARK_FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1
            assert table.get_row_at(0)[1] == INBOX
            assert INVOICE in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_next_step_is_the_unmarked_view(app):
        async with app.run_test() as pilot:
            await open_files_and_mark_first(pilot)
            await pilot.press(MARK_FILTER_KEY, MARK_FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1
            assert table.get_row_at(0)[1] == NOTES
            assert UNMARKED in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_wraps_back_to_any_mark(app):
        async with app.run_test() as pilot:
            await open_files_and_mark_first(pilot)
            for _ in range(1 + 2):  # the mark, unmarked, then back round
                await pilot.press(MARK_FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1 + 1  # both files again
            assert ANY_MARK in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_with_nothing_marked_it_steps_straight_to_unmarked(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, MARK_FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1 + 1  # neither file carries anything
            assert UNMARKED in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_a_filter_matching_nothing_says_so(app):
        async with app.run_test() as pilot:
            await open_files_and_mark_first(pilot)
            await pilot.press(DOWN_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(MARK_FILTER_KEY, MARK_FILTER_KEY)
            message = pilot.app.screen.query_one("#no-files", Static)

            assert message.display
            assert NO_MATCHES_MESSAGE in str(message.render())
            assert not pilot.app.screen.query_one("#files", DataTable).display


class TestMarksScreen:
    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_says_so_when_nothing_is_marked(app):
        async with app.run_test() as pilot:
            await pilot.press(MARKS_KEY)
            message = pilot.app.screen.query_one("#no-marks", Static)

            assert message.display
            assert NO_MARKS_MESSAGE in str(message.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_lists_a_mark_with_its_count(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(BACK_KEY)
            await pilot.pause()
            await pilot.press(MARKS_KEY)
            table = pilot.app.screen.query_one("#marks", DataTable)

            assert table.get_row_at(0) == [INVOICE, "1"]

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_a_mark_on_two_files_counts_twice(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(DOWN_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(BACK_KEY)
            await pilot.pause()
            await pilot.press(MARKS_KEY)
            table = pilot.app.screen.query_one("#marks", DataTable)

            assert table.get_row_at(0) == [INVOICE, "2"]

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_marks_are_ordered_by_name(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, ADD_KEY)
            await type_name(pilot, INVOICE)
            await pilot.press(ADD_KEY)
            await type_name(pilot, HOLIDAY)
            await pilot.press(BACK_KEY)
            await pilot.pause()
            await pilot.press(MARKS_KEY)
            table = pilot.app.screen.query_one("#marks", DataTable)

            assert [table.get_row_at(row)[0] for row in range(table.row_count)] == [
                HOLIDAY,
                INVOICE,
            ]
