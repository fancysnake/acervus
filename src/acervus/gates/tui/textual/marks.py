"""The marks screen — lists every mark in use, with how many files carry it."""

from typing import TYPE_CHECKING, ClassVar, override

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.table import fill_table

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.mark import MarkServiceProtocol, MarkSummary

NO_MARKS_MESSAGE = "No marks yet. Put one on a file from the files screen."


class MarksScreen(Screen[None]):
    """Shows every mark in use, with how many files carry it."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "app.pop_screen", "Back")]

    def __init__(self, marks: MarkServiceProtocol) -> None:
        super().__init__()
        self._marks = marks
        self._listed: list[MarkSummary] = []

    # The widget tree does not depend on the data, so query_one never has to.
    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="marks")
        yield Static(NO_MARKS_MESSAGE, id="no-marks")
        yield Footer()

    def on_mount(self) -> None:
        self._listed = self._marks.list_all()
        fill_table(
            self.query_one("#marks", DataTable),
            columns=("Mark", "Files"),
            rows=[(mark.name, str(mark.file_count)) for mark in self._listed],
        )
        self.query_one("#marks", DataTable).display = bool(self._listed)
        self.query_one("#no-marks", Static).display = not self._listed
