"""Integration tests for the files screen, over a real database.

The files screen is pushed on top of the roots screen, so every query here
goes through ``pilot.app.screen`` — ``pilot.app.query`` resolves against the
default screen and would never see it.
"""

from pathlib import Path

import pytest
from textual.widgets import DataTable, Static

DOCS = "docs"
PHOTOS = "photos"
INBOX = "inbox.md"
SNAP = "holiday/snap.txt"
CONTENT = "hello"
FILES_KEY = "f"
FILTER_KEY = "r"
BACK_KEY = "escape"
NO_FILES_MESSAGE = "No files indexed"
ALL_ROOTS = "all roots"


@pytest.fixture(name="trees")
def trees_fixture(*, tmp_path):
    docs = tmp_path / "docs"
    photos = tmp_path / "photos"
    for tree, relative_path in ((docs, INBOX), (photos, SNAP)):
        target = tree / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(CONTENT)
    return {DOCS: docs, PHOTOS: photos}


def index(services, trees) -> None:
    services.roots.sync(trees)
    for alias in trees:
        services.scan.scan(alias)


class TestFilesScreen:
    @staticmethod
    async def test_it_lists_every_indexed_file(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == 1 + 1  # one file under each root

    @staticmethod
    async def test_a_row_names_the_root_and_the_path(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[:2] == [DOCS, INBOX]

    @staticmethod
    async def test_a_row_carries_the_size(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(0)[2] == str(len(CONTENT))

    @staticmethod
    async def test_a_nested_path_is_shown_whole(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.get_row_at(1)[:2] == [PHOTOS, str(Path(SNAP))]

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
    async def test_it_starts_unfiltered(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert ALL_ROOTS in str(label.render())

    @staticmethod
    async def test_the_filter_narrows_to_one_root(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            await pilot.press(FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1
            assert table.get_row_at(0)[0] == DOCS
            assert DOCS in str(label.render())

    @staticmethod
    async def test_the_filter_steps_to_the_next_root(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            await pilot.press(FILTER_KEY)
            await pilot.press(FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)

            assert table.row_count == 1
            assert table.get_row_at(0)[0] == PHOTOS

    @staticmethod
    async def test_the_filter_wraps_back_to_all_roots(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            for _ in range(1 + 2):  # past docs and photos, back to the start
                await pilot.press(FILTER_KEY)
            table = pilot.app.screen.query_one("#files", DataTable)
            label = pilot.app.screen.query_one("#file-filter", Static)

            assert table.row_count == 1 + 1  # both roots again
            assert ALL_ROOTS in str(label.render())

    @staticmethod
    async def test_back_returns_to_the_roots(*, app, services, trees):
        index(services, trees)

        async with app.run_test() as pilot:
            await pilot.press(FILES_KEY)
            await pilot.press(BACK_KEY)
            await pilot.pause()

            assert pilot.app.screen.query("#roots")
            assert not pilot.app.screen.query("#files")
