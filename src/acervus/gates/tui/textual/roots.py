"""The roots screen — lists the roots Acervus has indexed, and scans them."""

from typing import TYPE_CHECKING, ClassVar, override

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.table import fill_table
from acervus.pacts.root import RootUnavailableError

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

    def __init__(
        self, *, roots: RootServiceProtocol, scan: ScanServiceProtocol
    ) -> None:
        super().__init__()
        self._roots = roots
        self._scan = scan
        self._listed: list[RootDTO] = []

    # The widget tree does not depend on the data, so query_one never has to.
    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="roots")
        yield Static(NO_ROOTS_MESSAGE, id="no-roots")
        yield Static(id="scan-result")
        yield Footer()

    def on_mount(self) -> None:
        self._listed = self._roots.list_all()
        fill_table(
            self.query_one("#roots", DataTable),
            columns=("Alias", "Path"),
            rows=[(root.alias, str(root.path)) for root in self._listed],
        )
        self.query_one("#roots", DataTable).display = bool(self._listed)
        self.query_one("#no-roots", Static).display = not self._listed

    def action_scan(self) -> None:
        """Scan the root under the cursor and report what changed."""
        if (alias := self._under_cursor()) is None:
            return
        try:
            result = self._scan.scan(alias)
        except RootUnavailableError as error:
            self._report(str(error))
            return
        self._report(
            SCAN_RESULT.format(
                alias=alias,
                added=result.added,
                removed=result.removed,
                updated=result.updated,
            )
        )

    def _under_cursor(self) -> str | None:
        table = self.query_one("#roots", DataTable)
        if not 0 <= table.cursor_row < len(self._listed):
            return None
        return self._listed[table.cursor_row].alias

    def _report(self, message: str) -> None:
        self.query_one("#scan-result", Static).update(message)
