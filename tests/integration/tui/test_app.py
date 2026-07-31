"""Integration tests for the Acervus TUI app."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import DataTable, Static

from acervus.gates.tui.textual.app import AcervusApp

DB_PATH = Path("/tmp/acervus.db")
ROOTS = {"docs": Path("/home/user/docs")}
NO_ROOTS_MESSAGE = "No roots configured"


class TestAcervusApp:
    @staticmethod
    async def test_displays_roots():
        app = AcervusApp(db_path=DB_PATH, roots=ROOTS)

        async with app.run_test() as pilot:
            db_widget = pilot.app.query_one("#db-path", Static)
            table = pilot.app.query_one("#roots", DataTable)

            assert str(DB_PATH) in str(db_widget.render())
            assert table.row_count == len(ROOTS)

    @staticmethod
    async def test_no_roots():
        app = AcervusApp(db_path=DB_PATH, roots={})

        async with app.run_test() as pilot:
            message = pilot.app.query_one("#no-roots", Static)

            assert NO_ROOTS_MESSAGE in str(message.render())
