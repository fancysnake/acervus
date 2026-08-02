"""The files screen — lists the files Acervus has indexed, and marks them."""

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.marks import MarkNamePrompt
from acervus.gates.tui.textual.stacks import StackNamePrompt
from acervus.pacts.file import BARE, Bare, FileFilter
from acervus.pacts.mark import InvalidMarkNameError, MarkNotFoundError
from acervus.pacts.stack import InvalidStackNameError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import FileDTO, FileServiceProtocol, Narrowing
    from acervus.pacts.mark import MarkServiceProtocol
    from acervus.pacts.root import RootDTO, RootServiceProtocol
    from acervus.pacts.stack import StackServiceProtocol

NO_FILES_MESSAGE = "No files indexed. Scan a root first."
NO_MATCHES_MESSAGE = "No files match this filter."
ALL_ROOTS = "all roots"
ANY_MARK = "any mark"
UNMARKED = "unmarked"
ANY_STACK = "any stack"
UNSTACKED_ONLY = "unstacked"
FILTER_LABEL = "Showing: {roots}, {marks}, {stacks}"
UNKNOWN_ALIAS = "?"
ADD_PROMPT = "Mark to add:"
REMOVE_PROMPT = "Mark to remove:"
MARKED = "Marked {path} {name}."
TOOK_OFF = "Took {name} off {path}."
CARRIES = "Marks: {names}"
CARRIES_NONE = "Marks: none"
STACK_PROMPT = "Stack to put it in:"
SITS_IN = "Stack: {name}"
SITS_LOOSE = "Stack: none"
STACKED = "Put {path} in {name}."
TOOK_OUT = "Took {path} out of its stack."


class FilesScreen(Screen[None]):
    """Shows indexed files, filterable by root, and marks the one under the cursor."""

    BINDINGS: ClassVar[list[BindingType]] = [
        # The filter keys take a consonant from the noun: mar(k), sta(c)k.
        ("r", "cycle_filter", "Filter by root"),
        ("k", "cycle_mark", "Filter by mark"),
        ("c", "cycle_stack", "Filter by stack"),
        ("a", "add_mark", "Add mark"),
        ("x", "remove_mark", "Remove mark"),
        ("s", "add_stack", "Put in stack"),
        ("u", "remove_stack", "Take out of stack"),
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(
        self,
        *,
        roots: RootServiceProtocol,
        files: FileServiceProtocol,
        marks: MarkServiceProtocol,
        stacks: StackServiceProtocol,
    ) -> None:
        super().__init__()
        self._roots = roots
        self._files = files
        self._marks = marks
        self._stacks = stacks
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
        yield Static(id="file-stack")
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
        self._scope = replace(
            self._scope, root_id=self._next(steps, self._scope.root_id)
        )
        self._refresh()

    def action_cycle_mark(self) -> None:
        """Step the mark filter on: any mark, then each mark, then unmarked."""
        steps = self._steps(mark.name for mark in self._marks.list_all())
        self._scope = replace(self._scope, mark=self._next(steps, self._scope.mark))
        self._refresh()

    def action_cycle_stack(self) -> None:
        """Step the stack filter on: any stack, then each stack, then unstacked."""
        steps = self._steps(stack.name for stack in self._stacks.list_all())
        self._scope = replace(self._scope, stack=self._next(steps, self._scope.stack))
        self._refresh()

    @staticmethod
    def _steps(names: Iterable[str]) -> list[Narrowing]:
        """Return the cycle: everything, then each name, then only the bare ones.

        Returns:
            One step per stop, starting at the unfiltered one.
        """
        return [None, *names, BARE]

    @staticmethod
    def _next[T](steps: list[T], current: T) -> T:
        """Return the step after this one, wrapping round at the end.

        A filter whose name has since been deleted is not in the cycle at all,
        so it restarts rather than raising.

        Returns:
            The step to move to.
        """
        standing = steps.index(current) if current in steps else 0
        return steps[(standing + 1) % len(steps)]

    def action_add_mark(self) -> None:
        """Ask for a name and put that mark on the file under the cursor."""
        if self._under_cursor() is not None:
            self.app.push_screen(MarkNamePrompt(ADD_PROMPT), self._add_mark)

    def action_remove_mark(self) -> None:
        """Ask for a name and take that mark off the file under the cursor."""
        if self._under_cursor() is not None:
            self.app.push_screen(MarkNamePrompt(REMOVE_PROMPT), self._remove_mark)

    def action_add_stack(self) -> None:
        """Ask for a name and put the file under the cursor in that stack."""
        if self._under_cursor() is not None:
            self.app.push_screen(StackNamePrompt(STACK_PROMPT), self._add_stack)

    def action_remove_stack(self) -> None:
        """Take the file under the cursor out of whatever stack it sits in."""
        if (file := self._under_cursor()) is None:
            return
        self._stacks.remove(file.id)
        self._report(TOOK_OUT.format(path=file.relative_path))
        self._show_carried()

    def _add_stack(self, name: str | None) -> None:
        file = self._under_cursor()
        if name is None or file is None:
            return
        try:
            stack = self._stacks.add(file.id, name=name)
        except InvalidStackNameError as error:
            self._report(str(error))
            return
        self._report(STACKED.format(path=file.relative_path, name=stack.name))
        self._show_carried()

    def _add_mark(self, name: str | None) -> None:
        file = self._under_cursor()
        if name is None or file is None:
            return
        try:
            mark = self._marks.add(file.id, name=name)
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
            self._marks.remove(file.id, name=name)
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
        sitting = self.query_one("#file-stack", Static)
        if (file := self._under_cursor()) is None:
            carried.update(CARRIES_NONE)
            sitting.update(SITS_LOOSE)
            return
        names = [mark.name for mark in self._marks.list_for_file(file.id)]
        carried.update(
            CARRIES.format(names=", ".join(names)) if names else CARRIES_NONE
        )
        stack = self._stacks.for_file(file.id)
        sitting.update(SITS_LOOSE if stack is None else SITS_IN.format(name=stack.name))

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
                marks=self._scope_label(
                    self._scope.mark, any_label=ANY_MARK, bare_label=UNMARKED
                ),
                stacks=self._scope_label(
                    self._scope.stack, any_label=ANY_STACK, bare_label=UNSTACKED_ONLY
                ),
            )
        )
        self._show_carried()

    @staticmethod
    def _scope_label(scope: Narrowing, *, any_label: str, bare_label: str) -> str:
        """Return the word describing one narrowing on the filter line.

        Returns:
            The label to show for this axis.
        """
        match scope:
            case None:
                return any_label
            case Bare.BARE:
                return bare_label
            case name:
                return name
