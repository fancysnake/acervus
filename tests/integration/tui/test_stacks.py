"""Integration tests for stacking files from the TUI, over a real database.

Files are put in stacks from the files screen and the stacks are listed on the
stacks screen, both of which are pushed, so queries go through
``pilot.app.screen``.
"""

from __future__ import annotations

import pytest
from textual.widgets import DataTable, Static

INBOX = "inbox.md"
NOTES = "notes.md"
TRIP = "iceland trip"
TAXES = "taxes 2026"
FILES_KEY = "f"
STACKS_KEY = "t"
PUT_KEY = "s"
TAKE_KEY = "u"
BACK_KEY = "escape"
DOWN_KEY = "down"
SUBMIT_KEY = "enter"
NO_STACKS_MESSAGE = "No stacks yet"
SITS_LOOSE = "Stack: none"
EMPTY_NAME = "   "
REJECTED = "blank"


async def type_name(pilot, name: str) -> None:
    await pilot.press(*name, SUBMIT_KEY)


async def stack_first(pilot, name: str = TRIP) -> None:
    """Open the files screen and put the first file, inbox.md, in a stack."""
    await pilot.press(FILES_KEY, PUT_KEY)
    await type_name(pilot, name)


class TestPuttingAFileInAStack:
    @staticmethod
    async def test_it_reaches_the_index(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)

        assert [stack.name for stack in indexed.stacks.list_all()] == [TRIP]

    @staticmethod
    async def test_it_lands_on_the_file_under_the_cursor(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)

        first, second = indexed.files.list_all()
        assert indexed.stacks.for_file(first.id).name == TRIP
        assert indexed.stacks.for_file(second.id) is None

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_screen_shows_the_stack(app):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            sitting = pilot.app.screen.query_one("#file-stack", Static)

            assert TRIP in str(sitting.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_a_loose_file_says_so(app):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            sitting = pilot.app.screen.query_one("#file-stack", Static)

            assert SITS_LOOSE in str(sitting.render())

    @staticmethod
    async def test_backing_out_of_the_prompt_stacks_nothing(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, PUT_KEY)
            await pilot.press(*TRIP, BACK_KEY)

        assert indexed.stacks.list_all() == []

    @staticmethod
    async def test_a_blank_name_is_reported_and_not_stored(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, PUT_KEY)
            await type_name(pilot, EMPTY_NAME)
            status = pilot.app.screen.query_one("#mark-status", Static)

            assert REJECTED in str(status.render())

        assert indexed.stacks.list_all() == []

    @staticmethod
    async def test_two_files_can_share_a_stack(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(DOWN_KEY, PUT_KEY)
            await type_name(pilot, TRIP)

        assert indexed.stacks.list_all()[0].file_count == 1 + 1  # both files


class TestMovingBetweenStacks:
    @staticmethod
    async def test_a_file_leaves_the_stack_it_was_in(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(PUT_KEY)
            await type_name(pilot, TAXES)

        first = indexed.files.list_all()[0]
        assert indexed.stacks.for_file(first.id).name == TAXES

    @staticmethod
    async def test_the_stack_it_emptied_is_gone(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(PUT_KEY)
            await type_name(pilot, TAXES)

        assert [stack.name for stack in indexed.stacks.list_all()] == [TAXES]

    @staticmethod
    async def test_a_stack_another_file_still_fills_survives(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(DOWN_KEY, PUT_KEY)
            await type_name(pilot, TRIP)
            await pilot.press(PUT_KEY)
            await type_name(pilot, TAXES)

        assert [stack.name for stack in indexed.stacks.list_all()] == [TRIP, TAXES]


class TestTakingAFileOut:
    @staticmethod
    async def test_it_leaves_the_stack(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(TAKE_KEY)

        first = indexed.files.list_all()[0]
        assert indexed.stacks.for_file(first.id) is None

    @staticmethod
    async def test_an_emptied_stack_is_deleted(app, indexed):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(TAKE_KEY)

        assert indexed.stacks.list_all() == []

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_the_screen_says_the_file_is_loose(app):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(TAKE_KEY)
            sitting = pilot.app.screen.query_one("#file-stack", Static)

            assert SITS_LOOSE in str(sitting.render())

    @staticmethod
    async def test_taking_a_loose_file_out_is_harmless(app, indexed):
        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY, TAKE_KEY)

        assert indexed.stacks.list_all() == []


class TestStacksScreen:
    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_says_so_when_nothing_is_stacked(app):
        async with app.run_test() as pilot:
            await pilot.press(STACKS_KEY)
            message = pilot.app.screen.query_one("#no-stacks", Static)

            assert NO_STACKS_MESSAGE in str(message.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_lists_a_stack_with_its_size(app):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(BACK_KEY)
            await pilot.pause()
            await pilot.press(STACKS_KEY)
            table = pilot.app.screen.query_one("#stacks", DataTable)

            assert table.get_row_at(0) == [TRIP, "1"]

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_it_shows_the_contents_of_the_stack_under_the_cursor(app):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(BACK_KEY)
            await pilot.pause()
            await pilot.press(STACKS_KEY)
            contents = pilot.app.screen.query_one("#stack-contents", Static)
            label = pilot.app.screen.query_one("#stack-contents-label", Static)

            assert INBOX in str(contents.render())
            assert NOTES not in str(contents.render())
            assert TRIP in str(label.render())

    @staticmethod
    @pytest.mark.usefixtures("indexed")
    async def test_stacks_are_ordered_by_name(app):
        async with app.run_test() as pilot:
            await stack_first(pilot)
            await pilot.press(DOWN_KEY, PUT_KEY)
            await type_name(pilot, TAXES)
            await pilot.press(BACK_KEY)
            await pilot.pause()
            await pilot.press(STACKS_KEY)
            table = pilot.app.screen.query_one("#stacks", DataTable)

            assert [table.get_row_at(row)[0] for row in range(table.row_count)] == [
                TRIP,
                TAXES,
            ]
