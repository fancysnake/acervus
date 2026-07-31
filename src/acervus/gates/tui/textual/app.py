"""Textual TUI application — interactive browser for Acervus."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from pathlib import Path

    from textual.binding import BindingType


class AcervusApp(App[None]):
    """Interactive browser for configured roots."""

    TITLE = "Acervus"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, db_path: Path, roots: dict[str, Path]) -> None:
        super().__init__()
        self._db_path = db_path
        self._roots = roots

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Database: {self._db_path}", id="db-path")
        if self._roots:
            yield DataTable(id="roots")
        else:
            yield Static("No roots configured.", id="no-roots")
        yield Footer()

    def on_mount(self) -> None:
        if not self._roots:
            return
        table = self.query_one("#roots", DataTable)
        table.add_columns("Alias", "Path")
        for alias, path in self._roots.items():
            table.add_row(alias, str(path))
