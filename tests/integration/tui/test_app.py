"""Integration tests for the Acervus TUI, over a real database."""

# Pytest supplies fixtures by name, so a test taking three of them is not the
# argument-order hazard the positional limit guards against.
# pylint: disable=too-many-positional-arguments


from pathlib import Path

import pytest
from textual.widgets import DataTable, Static

DOCS = "docs"
DOCS_PATH = Path("/home/user/docs")
PHOTOS = "photos"
PHOTOS_PATH = Path("/home/user/photos")
NO_ROOTS_MESSAGE = "No roots configured"
SCAN_KEY = "s"
NOTHING_ADDED = "0 added"
BOTH_ADDED = "2 added"
ONE_REMOVED = "1 removed"
ONE_UPDATED = "1 updated"
INBOX = "inbox.md"
LONGER = "hello again, and then some"


@pytest.fixture(name="root_dir")
def root_dir_fixture(tmp_path):
    root_dir = tmp_path / "tree"
    root_dir.mkdir()
    return root_dir


def write(root_dir: Path, relative_path: str) -> None:
    target = root_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hello")


class TestRootsScreen:
    @staticmethod
    async def test_displays_the_indexed_roots(app, services):
        services.roots.sync({DOCS: DOCS_PATH, PHOTOS: PHOTOS_PATH})

        async with app.run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert table.row_count == 1 + 1  # docs + photos

    @staticmethod
    async def test_a_row_carries_the_alias_and_the_path(app, services):
        services.roots.sync({DOCS: DOCS_PATH})

        async with app.run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert table.get_row_at(0) == [DOCS, str(DOCS_PATH)]

    @staticmethod
    async def test_the_rows_are_ordered_by_alias(app, services):
        services.roots.sync({PHOTOS: PHOTOS_PATH, DOCS: DOCS_PATH})

        async with app.run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert [table.get_row_at(row)[0] for row in range(table.row_count)] == [
                DOCS,
                PHOTOS,
            ]

    @staticmethod
    async def test_an_empty_index_says_so(app):
        async with app.run_test() as pilot:
            message = pilot.app.query_one("#no-roots", Static)

            assert NO_ROOTS_MESSAGE in str(message.render())

    @staticmethod
    async def test_an_empty_index_shows_no_table(app):
        async with app.run_test() as pilot:
            assert not pilot.app.query("#roots")

    @staticmethod
    async def test_a_root_dropped_from_the_config_is_gone(app, services):
        services.roots.sync({DOCS: DOCS_PATH, PHOTOS: PHOTOS_PATH})
        services.roots.sync({DOCS: DOCS_PATH})

        async with app.run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert table.row_count == 1
            assert table.get_row_at(0) == [DOCS, str(DOCS_PATH)]


class TestScanAction:
    @staticmethod
    async def test_it_reports_what_the_scan_added(app, services, root_dir):
        write(root_dir, "notes/todo.md")
        write(root_dir, "inbox.md")
        services.roots.sync({DOCS: root_dir})

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert BOTH_ADDED in str(status.render())

    @staticmethod
    async def test_it_names_the_root_it_scanned(app, services, root_dir):
        write(root_dir, "inbox.md")
        services.roots.sync({DOCS: root_dir})

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert DOCS in str(status.render())

    @staticmethod
    async def test_the_files_reach_the_index(app, services, repositories, root_dir):
        write(root_dir, "inbox.md")
        root = services.roots.sync({DOCS: root_dir})[0]

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)

        assert len(repositories.files.list_by_root(root.id)) == 1

    @staticmethod
    async def test_an_empty_root_reports_nothing_added(app, services, root_dir):
        services.roots.sync({DOCS: root_dir})

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert NOTHING_ADDED in str(status.render())

    @staticmethod
    async def test_a_second_scan_adds_nothing(app, services, root_dir):
        write(root_dir, "inbox.md")
        services.roots.sync({DOCS: root_dir})

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert NOTHING_ADDED in str(status.render())

    @staticmethod
    async def test_it_scans_the_selected_root(app, services, root_dir, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        write(root_dir, "inbox.md")
        services.roots.sync({DOCS: root_dir, PHOTOS: other})

        async with app.run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)
            table.move_cursor(row=1)
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert PHOTOS in str(status.render())
            assert NOTHING_ADDED in str(status.render())

    @staticmethod
    async def test_a_deleted_file_leaves_the_index(
        app, services, repositories, root_dir
    ):
        write(root_dir, INBOX)
        root = services.roots.sync({DOCS: root_dir})[0]

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)
            (root_dir / INBOX).unlink()
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert ONE_REMOVED in str(status.render())

        assert not repositories.files.list_by_root(root.id)

    @staticmethod
    async def test_a_changed_file_is_rewritten(app, services, repositories, root_dir):
        write(root_dir, INBOX)
        root = services.roots.sync({DOCS: root_dir})[0]

        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)
            (root_dir / INBOX).write_text(LONGER)
            await pilot.press(SCAN_KEY)
            status = pilot.app.query_one("#scan-result", Static)

            assert ONE_UPDATED in str(status.render())

        assert repositories.files.list_by_root(root.id)[0].size == len(LONGER)

    @staticmethod
    async def test_scanning_an_empty_index_does_nothing(app):
        async with app.run_test() as pilot:
            await pilot.press(SCAN_KEY)

            assert not pilot.app.query("#scan-result")
