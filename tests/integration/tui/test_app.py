"""Integration tests for the Acervus TUI, over a real database."""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import DataTable, Static

from acervus.gates.tui.textual.app import AcervusApp
from acervus.inits.repositories import Repositories
from acervus.inits.services import Services

DOCS = "docs"
DOCS_PATH = Path("/home/user/docs")
PHOTOS = "photos"
PHOTOS_PATH = Path("/home/user/photos")
NO_ROOTS_MESSAGE = "No roots configured"


@pytest.fixture(name="services")
def services_fixture(tmp_path):
    return Services(Repositories(tmp_path / "acervus.db"))


class TestAcervusApp:
    @staticmethod
    async def test_displays_the_indexed_roots(services):
        services.roots.sync({DOCS: DOCS_PATH, PHOTOS: PHOTOS_PATH})

        async with AcervusApp(services.roots).run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert table.row_count == 1 + 1  # docs + photos

    @staticmethod
    async def test_a_row_carries_the_alias_and_the_path(services):
        services.roots.sync({DOCS: DOCS_PATH})

        async with AcervusApp(services.roots).run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert table.get_row_at(0) == [DOCS, str(DOCS_PATH)]

    @staticmethod
    async def test_the_rows_are_ordered_by_alias(services):
        services.roots.sync({PHOTOS: PHOTOS_PATH, DOCS: DOCS_PATH})

        async with AcervusApp(services.roots).run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert [table.get_row_at(row)[0] for row in range(table.row_count)] == [
                DOCS,
                PHOTOS,
            ]

    @staticmethod
    async def test_an_empty_index_says_so(services):
        async with AcervusApp(services.roots).run_test() as pilot:
            message = pilot.app.query_one("#no-roots", Static)

            assert NO_ROOTS_MESSAGE in str(message.render())

    @staticmethod
    async def test_an_empty_index_shows_no_table(services):
        async with AcervusApp(services.roots).run_test() as pilot:
            assert not pilot.app.query("#roots")

    @staticmethod
    async def test_a_root_dropped_from_the_config_is_gone(services):
        services.roots.sync({DOCS: DOCS_PATH, PHOTOS: PHOTOS_PATH})
        services.roots.sync({DOCS: DOCS_PATH})

        async with AcervusApp(services.roots).run_test() as pilot:
            table = pilot.app.query_one("#roots", DataTable)

            assert table.row_count == 1
            assert table.get_row_at(0) == [DOCS, str(DOCS_PATH)]
