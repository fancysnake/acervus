"""The files screen — lists the files Acervus has indexed."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import FileServiceProtocol
    from acervus.pacts.root import RootDTO, RootServiceProtocol

NO_FILES_MESSAGE = "No files indexed. Scan a root first."
ALL_ROOTS = "all roots"
FILTER_LABEL = "Showing: {scope}"
UNKNOWN_ALIAS = "?"


class FilesScreen(Screen[None]):
    """Shows indexed files as ``alias:relative/path``, filterable by root."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "cycle_filter", "Filter by root"),
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, roots: RootServiceProtocol, files: FileServiceProtocol) -> None:
        super().__init__()
        self._roots = roots
        self._files = files
        self._listed: list[RootDTO] = []
        self._filter: int | None = None

    def compose(self) -> ComposeResult:
        self._listed = self._roots.list_all()
        yield Header()
        yield Static(id="file-filter")
        yield DataTable(id="files")
        yield Static(NO_FILES_MESSAGE, id="no-files")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#files", DataTable).add_columns("Root", "Path", "Size")
        self._refresh()

    def action_cycle_filter(self) -> None:
        """Step the root filter on by one, wrapping back to all roots."""
        if not self._listed:
            return
        aliases: list[int | None] = [None, *(root.id for root in self._listed)]
        self._filter = aliases[(aliases.index(self._filter) + 1) % len(aliases)]
        self._refresh()

    def _refresh(self) -> None:
        by_id = {root.id: root.alias for root in self._listed}
        listed = self._files.list_all(self._filter)

        table = self.query_one("#files", DataTable)
        table.clear()
        for file in listed:
            table.add_row(
                by_id.get(file.root_id, UNKNOWN_ALIAS),
                str(file.relative_path),
                str(file.size),
            )

        table.display = bool(listed)
        self.query_one("#no-files", Static).display = not listed
        self.query_one("#file-filter", Static).update(
            FILTER_LABEL.format(
                scope=ALL_ROOTS if self._filter is None else by_id[self._filter]
            )
        )
