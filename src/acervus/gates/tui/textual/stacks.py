"""The stacks screen — lists every stack, and what sits in the one selected."""

from typing import TYPE_CHECKING, ClassVar, override

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

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
        self._held: dict[int, list[str]] = {}

    # The widget tree does not depend on the data, so query_one never has to.
    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="stacks")
        yield Static(NO_STACKS_MESSAGE, id="no-stacks")
        yield Static(id="stack-contents-label")
        yield Static(id="stack-contents")
        yield Footer()

    def on_mount(self) -> None:
        self._listed = self._stacks.list_all()
        fill_table(
            self.query_one("#stacks", DataTable),
            columns=("Stack", "Files"),
            rows=[(stack.name, str(stack.file_count)) for stack in self._listed],
        )
        self.query_one("#stacks", DataTable).display = bool(self._listed)
        self.query_one("#no-stacks", Static).display = not self._listed
        self._show_contents()

    def on_data_table_row_highlighted(self) -> None:
        """Show what sits in whichever stack the cursor has reached."""
        self._show_contents()

    def _show_contents(self) -> None:
        if (stack := self._under_cursor()) is None:
            return
        self.query_one("#stack-contents-label", Static).update(
            CONTENTS_LABEL.format(name=stack.name)
        )
        self.query_one("#stack-contents", Static).update(
            "\n".join(self._contents_of(stack)) or EMPTY_CONTENTS
        )

    def _contents_of(self, stack: StackSummary) -> list[str]:
        """Return the paths in this stack, reading them at most once.

        Held by stack id rather than re-read per keystroke: the cursor moves
        one row at a time, and every move would otherwise be a query.

        Returns:
            One relative path per file in the stack.
        """
        if stack.id not in self._held:
            self._held[stack.id] = [
                str(file.relative_path)
                for file in self._files.list_all(FileFilter(stack=stack.name))
            ]
        return self._held[stack.id]

    def _under_cursor(self) -> StackSummary | None:
        table = self.query_one("#stacks", DataTable)
        if not 0 <= table.cursor_row < len(self._listed):
            return None
        return self._listed[table.cursor_row]
