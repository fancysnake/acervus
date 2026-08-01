"""The files screen — lists the files Acervus has indexed, and marks them."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.marks import MarkNamePrompt
from acervus.pacts.file import FileFilter
from acervus.pacts.mark import InvalidMarkNameError, MarkNotFoundError

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import FileDTO, FileServiceProtocol
    from acervus.pacts.mark import MarkServiceProtocol
    from acervus.pacts.root import RootDTO, RootServiceProtocol

NO_FILES_MESSAGE = "No files indexed. Scan a root first."
NO_MATCHES_MESSAGE = "No files match this filter."
ALL_ROOTS = "all roots"
ANY_MARK = "any mark"
UNMARKED = "unmarked"
FILTER_LABEL = "Showing: {roots}, {marks}"
UNKNOWN_ALIAS = "?"
ADD_PROMPT = "Mark to add:"
REMOVE_PROMPT = "Mark to remove:"
MARKED = "Marked {path} {name}."
TOOK_OFF = "Took {name} off {path}."
CARRIES = "Marks: {names}"
CARRIES_NONE = "Marks: none"


class FilesScreen(Screen[None]):
    """Shows indexed files, filterable by root, and marks the one under the cursor."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "cycle_filter", "Filter by root"),
        ("k", "cycle_mark", "Filter by mark"),
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
        self._scope = FileFilter()

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
        steps: list[int | None] = [None, *(root.id for root in self._listed)]
        standing = (
            steps.index(self._scope.root_id) if self._scope.root_id in steps else 0
        )
        self._scope = replace(self._scope, root_id=steps[(standing + 1) % len(steps)])
        self._refresh()

    def action_cycle_mark(self) -> None:
        """Step the mark filter on: any mark, then each mark, then unmarked."""
        steps: list[tuple[str | None, bool]] = [
            (None, False),
            *((mark.name, False) for mark in self._marks.list_all()),
            (None, True),
        ]
        current = (self._scope.mark, self._scope.unmarked)
        standing = steps.index(current) if current in steps else 0
        mark, unmarked = steps[(standing + 1) % len(steps)]
        self._scope = replace(self._scope, mark=mark, unmarked=unmarked)
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
        self._report(TOOK_OFF.format(name=name.strip(), path=file.relative_path))
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
        self._shown = self._files.list_all(self._scope)

        table = self.query_one("#files", DataTable)
        table.clear()
        for file in self._shown:
            table.add_row(
                by_id.get(file.root_id, UNKNOWN_ALIAS),
                str(file.relative_path),
                str(file.size),
            )

        table.display = bool(self._shown)
        empty = self.query_one("#no-files", Static)
        empty.display = not self._shown
        empty.update(
            NO_FILES_MESSAGE if self._scope == FileFilter() else NO_MATCHES_MESSAGE
        )
        root_id = self._scope.root_id
        self.query_one("#file-filter", Static).update(
            FILTER_LABEL.format(
                roots=ALL_ROOTS if root_id is None else by_id[root_id],
                marks=self._mark_scope(),
            )
        )
        self._show_carried()

    def _mark_scope(self) -> str:
        if self._scope.unmarked:
            return UNMARKED
        return ANY_MARK if self._scope.mark is None else self._scope.mark
