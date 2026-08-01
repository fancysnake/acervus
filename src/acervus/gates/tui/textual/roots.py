"""The roots screen — lists the roots Acervus has indexed, and scans them."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import ScanServiceProtocol
    from acervus.pacts.root import RootDTO, RootServiceProtocol

NO_ROOTS_MESSAGE = "No roots configured."
SCAN_RESULT = "{alias}: {added} added, {removed} removed, {updated} updated."


class RootsScreen(Screen[None]):
    """Shows every indexed root, and scans the one under the cursor."""

    BINDINGS: ClassVar[list[BindingType]] = [("s", "scan", "Scan")]

    def __init__(self, roots: RootServiceProtocol, scan: ScanServiceProtocol) -> None:
        super().__init__()
        self._roots = roots
        self._scan = scan
        self._listed: list[RootDTO] = []

    def compose(self) -> ComposeResult:
        self._listed = self._roots.list_all()
        yield Header()
        if self._listed:
            yield DataTable(id="roots")
            yield Static(id="scan-result")
        else:
            yield Static(NO_ROOTS_MESSAGE, id="no-roots")
        yield Footer()

    def on_mount(self) -> None:
        if not self._listed:
            return
        table = self.query_one("#roots", DataTable)
        table.cursor_type = "row"
        table.add_columns("Alias", "Path")
        for root in self._listed:
            table.add_row(root.alias, str(root.path))

    def action_scan(self) -> None:
        """Scan the root under the cursor and report what changed."""
        if not self._listed:
            return
        table = self.query_one("#roots", DataTable)
        alias = self._listed[table.cursor_row].alias
        result = self._scan.scan(alias)
        self.query_one("#scan-result", Static).update(
            SCAN_RESULT.format(
                alias=alias,
                added=result.added,
                removed=result.removed,
                updated=result.updated,
            )
        )
