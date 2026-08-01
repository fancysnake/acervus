"""The files screen — lists the files Acervus has indexed, and marks them."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.marks import MarkNamePrompt
from acervus.pacts.mark import InvalidMarkNameError, MarkNotFoundError

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import FileDTO, FileServiceProtocol
    from acervus.pacts.mark import MarkServiceProtocol
    from acervus.pacts.root import RootDTO, RootServiceProtocol

NO_FILES_MESSAGE = "No files indexed. Scan a root first."
ALL_ROOTS = "all roots"
FILTER_LABEL = "Showing: {scope}"
UNKNOWN_ALIAS = "?"
ADD_PROMPT = "Mark to add:"
REMOVE_PROMPT = "Mark to remove:"
MARKED = "Marked {path} {name}."
UNMARKED = "Took {name} off {path}."
CARRIES = "Marks: {names}"
CARRIES_NONE = "Marks: none"


class FilesScreen(Screen[None]):
    """Shows indexed files, filterable by root, and marks the one under the cursor."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "cycle_filter", "Filter by root"),
        ("a", "add_mark", "Add mark"),
        ("x", "remove_mark", "Remove mark"),
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(
        self,
        roots: RootServiceProtocol,
        files: FileServiceProtocol,
        marks: MarkServiceProtocol,
    ) -> None:
        super().__init__()
        self._roots = roots
        self._files = files
        self._marks = marks
        self._listed: list[RootDTO] = []
        self._shown: list[FileDTO] = []
        self._filter: int | None = None

    def compose(self) -> ComposeResult:
        self._listed = self._roots.list_all()
        yield Header()
        yield Static(id="file-filter")
        yield DataTable(id="files")
        yield Static(NO_FILES_MESSAGE, id="no-files")
        yield Static(id="file-marks")
        yield Static(id="mark-status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#files", DataTable)
        table.cursor_type = "row"
        table.add_columns("Root", "Path", "Size")
        self._refresh()

    def on_data_table_row_highlighted(self) -> None:
        """Show the marks carried by whichever file the cursor has reached."""
        self._show_carried()

    def action_cycle_filter(self) -> None:
        """Step the root filter on by one, wrapping back to all roots."""
        if not self._listed:
            return
        scopes: list[int | None] = [None, *(root.id for root in self._listed)]
        self._filter = scopes[(scopes.index(self._filter) + 1) % len(scopes)]
        self._refresh()

    def action_add_mark(self) -> None:
        """Ask for a name and put that mark on the file under the cursor."""
        if self._under_cursor() is not None:
            self.app.push_screen(MarkNamePrompt(ADD_PROMPT), self._add_mark)

    def action_remove_mark(self) -> None:
        """Ask for a name and take that mark off the file under the cursor."""
        if self._under_cursor() is not None:
            self.app.push_screen(MarkNamePrompt(REMOVE_PROMPT), self._remove_mark)

    def _add_mark(self, name: str | None) -> None:
        file = self._under_cursor()
        if name is None or file is None:
            return
        try:
            mark = self._marks.add(file.id, name)
        except InvalidMarkNameError as error:
            self._report(str(error))
            return
        self._report(MARKED.format(path=file.relative_path, name=mark.name))
        self._show_carried()

    def _remove_mark(self, name: str | None) -> None:
        file = self._under_cursor()
        if name is None or file is None:
            return
        try:
            self._marks.remove(file.id, name)
        except (InvalidMarkNameError, MarkNotFoundError) as error:
            self._report(str(error))
            return
        self._report(UNMARKED.format(name=name.strip(), path=file.relative_path))
        self._show_carried()

    def _under_cursor(self) -> FileDTO | None:
        table = self.query_one("#files", DataTable)
        if not self._shown or not 0 <= table.cursor_row < len(self._shown):
            return None
        return self._shown[table.cursor_row]

    def _report(self, message: str) -> None:
        self.query_one("#mark-status", Static).update(message)

    def _show_carried(self) -> None:
        carried = self.query_one("#file-marks", Static)
        if (file := self._under_cursor()) is None:
            carried.update(CARRIES_NONE)
            return
        names = [mark.name for mark in self._marks.list_for_file(file.id)]
        carried.update(
            CARRIES.format(names=", ".join(names)) if names else CARRIES_NONE
        )

    def _refresh(self) -> None:
        by_id = {root.id: root.alias for root in self._listed}
        self._shown = self._files.list_all(self._filter)

        table = self.query_one("#files", DataTable)
        table.clear()
        for file in self._shown:
            table.add_row(
                by_id.get(file.root_id, UNKNOWN_ALIAS),
                str(file.relative_path),
                str(file.size),
            )

        table.display = bool(self._shown)
        self.query_one("#no-files", Static).display = not self._shown
        self.query_one("#file-filter", Static).update(
            FILTER_LABEL.format(
                scope=ALL_ROOTS if self._filter is None else by_id[self._filter]
            )
        )
        self._show_carried()
