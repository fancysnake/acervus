"""The marks screen, and the prompt used to name a mark."""

from typing import TYPE_CHECKING, ClassVar

from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from acervus.gates.tui.textual.table import fill_table

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.mark import MarkServiceProtocol, MarkSummary

NO_MARKS_MESSAGE = "No marks yet. Put one on a file from the files screen."


class MarkNamePrompt(ModalScreen[str | None]):
    """Asks for a mark name, returning it or ``None`` if the user backs out."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        yield Static(self._prompt, id="mark-prompt")
        yield Input(id="mark-name")

    def on_mount(self) -> None:
        self.query_one("#mark-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Hand the typed name back to whoever opened the prompt."""
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        """Back out without naming a mark."""
        self.dismiss(None)


class MarksScreen(Screen[None]):
    """Shows every mark in use, with how many files carry it."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "app.pop_screen", "Back")]

    def __init__(self, marks: MarkServiceProtocol) -> None:
        super().__init__()
        self._marks = marks
        self._listed: list[MarkSummary] = []

    def compose(self) -> ComposeResult:
        self._listed = self._marks.list_all()
        yield Header()
        if self._listed:
            yield DataTable(id="marks")
        else:
            yield Static(NO_MARKS_MESSAGE, id="no-marks")
        yield Footer()

    def on_mount(self) -> None:
        if not self._listed:
            return
        rows = [(mark.name, str(mark.file_count)) for mark in self._listed]
        fill_table(
            self.query_one("#marks", DataTable), columns=("Mark", "Files"), rows=rows
        )
