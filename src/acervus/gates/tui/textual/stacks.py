"""The stacks screen, and the prompt used to name a stack."""

from typing import TYPE_CHECKING, ClassVar

from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from acervus.gates.tui.textual.table import fill_table
from acervus.pacts.file import FileFilter

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import FileServiceProtocol
    from acervus.pacts.stack import StackServiceProtocol, StackSummary

NO_STACKS_MESSAGE = "No stacks yet. Put a file in one from the files screen."
CONTENTS_LABEL = "In {name}:"
EMPTY_CONTENTS = "(nothing)"


class StackNamePrompt(ModalScreen[str | None]):
    """Asks for a stack name, returning it or ``None`` if the user backs out."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        yield Static(self._prompt, id="stack-prompt")
        yield Input(id="stack-name")

    def on_mount(self) -> None:
        self.query_one("#stack-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Hand the typed name back to whoever opened the prompt."""
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        """Back out without naming a stack."""
        self.dismiss(None)


class StacksScreen(Screen[None]):
    """Shows every stack with its size, and what sits in the one under the cursor."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "app.pop_screen", "Back")]

    def __init__(
        self, *, stacks: StackServiceProtocol, files: FileServiceProtocol
    ) -> None:
        super().__init__()
        self._stacks = stacks
        self._files = files
        self._listed: list[StackSummary] = []

    def compose(self) -> ComposeResult:
        self._listed = self._stacks.list_all()
        yield Header()
        if self._listed:
            yield DataTable(id="stacks")
            yield Static(id="stack-contents-label")
            yield Static(id="stack-contents")
        else:
            yield Static(NO_STACKS_MESSAGE, id="no-stacks")
        yield Footer()

    def on_mount(self) -> None:
        if not self._listed:
            return
        rows = [(stack.name, str(stack.file_count)) for stack in self._listed]
        fill_table(
            self.query_one("#stacks", DataTable), columns=("Stack", "Files"), rows=rows
        )
        self._show_contents()

    def on_data_table_row_highlighted(self) -> None:
        """Show what sits in whichever stack the cursor has reached."""
        self._show_contents()

    def _show_contents(self) -> None:
        if (stack := self._under_cursor()) is None:
            return
        held = self._files.list_all(FileFilter(stack=stack.name))
        self.query_one("#stack-contents-label", Static).update(
            CONTENTS_LABEL.format(name=stack.name)
        )
        self.query_one("#stack-contents", Static).update(
            "\n".join(str(file.relative_path) for file in held) or EMPTY_CONTENTS
        )

    def _under_cursor(self) -> StackSummary | None:
        table = self.query_one("#stacks", DataTable)
        if not self._listed or not 0 <= table.cursor_row < len(self._listed):
            return None
        return self._listed[table.cursor_row]
