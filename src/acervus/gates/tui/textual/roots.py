"""The roots screen — lists the roots Acervus has indexed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from acervus.pacts.root import RootDTO, RootServiceProtocol

NO_ROOTS_MESSAGE = "No roots configured."


class RootsScreen(Screen[None]):
    """Shows every indexed root, or says there are none."""

    def __init__(self, roots: RootServiceProtocol) -> None:
        super().__init__()
        self._roots = roots
        self._listed: list[RootDTO] = []

    def compose(self) -> ComposeResult:
        self._listed = self._roots.list_all()
        yield Header()
        if self._listed:
            yield DataTable(id="roots")
        else:
            yield Static(NO_ROOTS_MESSAGE, id="no-roots")
        yield Footer()

    def on_mount(self) -> None:
        if not self._listed:
            return
        table = self.query_one("#roots", DataTable)
        table.add_columns("Alias", "Path")
        for root in self._listed:
            table.add_row(root.alias, str(root.path))
