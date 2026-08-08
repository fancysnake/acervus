"""The files screen — lists the files Acervus has indexed, and marks them."""

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, Protocol, override

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.prompt import NamePrompt
from acervus.gates.tui.textual.table import fill_table
from acervus.pacts.file import BARE, Bare, FileFilter
from acervus.pacts.mark import InvalidMarkNameError, MarkNotFoundError
from acervus.pacts.stack import InvalidStackNameError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import FileDTO, FileRepositoryProtocol, Narrowing
    from acervus.pacts.mark import MarkServiceProtocol
    from acervus.pacts.root import RootServiceProtocol
    from acervus.pacts.stack import StackServiceProtocol

NO_FILES_MESSAGE = "No files indexed. Scan a root first."
NO_MATCHES_MESSAGE = "No files match this filter."
ALL_ROOTS = "all roots"
ANY_MARK = "any mark"
UNMARKED = "unmarked"
ANY_STACK = "any stack"
UNSTACKED_ONLY = "unstacked"
FILTER_LABEL = "Showing: {roots}, {marks}, {stacks}"
UNKNOWN = "?"  # a root, mark or stack the screen has no name for
ROOTS = "roots"
MARKS = "marks"
STACKS = "stacks"
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
REJECTIONS = (InvalidMarkNameError, InvalidStackNameError, MarkNotFoundError)


class Operation(Protocol):
    """One thing the screen does to the file under the cursor."""

    def __call__(self, file: FileDTO, *, name: str) -> str:
        """Carry it out, returning what to report."""


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
        files: FileRepositoryProtocol,
        marks: MarkServiceProtocol,
        stacks: StackServiceProtocol,
    ) -> None:
        super().__init__()
        self._roots = roots
        self._files = files
        self._marks = marks
        self._stacks = stacks
        self._shown: list[FileDTO] = []
        self._scope = FileFilter()
        # The filter is keyed by id; this is what the filter line calls each of
        # them, one map per axis.
        self._named: dict[str, dict[int, str]] = {ROOTS: {}, MARKS: {}, STACKS: {}}

    # The widget tree does not depend on the data, so query_one never has to.
    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="file-filter")
        yield DataTable(id="files")
        yield Static(NO_FILES_MESSAGE, id="no-files")
        yield Static(id="file-marks")
        yield Static(id="file-stack")
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._named[ROOTS] = {root.id: root.alias for root in self._roots.list_all()}
        self._refresh()

    def on_data_table_row_highlighted(self) -> None:
        """Show the marks carried by whichever file the cursor has reached."""
        self._show_carried()

    def action_cycle_filter(self) -> None:
        """Step the root filter on by one, wrapping back to all roots."""
        named = self._named[ROOTS] = {
            root.id: root.alias for root in self._roots.list_all()
        }
        if not named:
            return
        # No bare step: every file has a root, so there is no rootless case.
        steps: list[int | None] = [None, *named]
        self._scope = replace(
            self._scope, root_id=self._next(steps, self._scope.root_id)
        )
        self._refresh()

    def action_cycle_mark(self) -> None:
        """Step the mark filter on: any mark, then each mark, then unmarked."""
        named = self._named[MARKS] = {
            mark.id: mark.name for mark in self._marks.list_all()
        }
        self._scope = replace(
            self._scope, mark_id=self._next(self._steps(named), self._scope.mark_id)
        )
        self._refresh()

    def action_cycle_stack(self) -> None:
        """Step the stack filter on: any stack, then each stack, then unstacked."""
        named = self._named[STACKS] = {
            stack.id: stack.name for stack in self._stacks.list_all()
        }
        self._scope = replace(
            self._scope, stack_id=self._next(self._steps(named), self._scope.stack_id)
        )
        self._refresh()

    @staticmethod
    def _steps(ids: Iterable[int]) -> list[Narrowing]:
        """Return the cycle: everything, then each one, then only the bare ones.

        Returns:
            One step per stop, starting at the unfiltered one.
        """
        return [None, *ids, BARE]

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
        self._ask(
            ADD_PROMPT, answer=lambda name: self._on_file(name, apply=self._marked)
        )

    def action_remove_mark(self) -> None:
        """Ask for a name and take that mark off the file under the cursor."""
        self._ask(
            REMOVE_PROMPT, answer=lambda name: self._on_file(name, apply=self._took_off)
        )

    def action_add_stack(self) -> None:
        """Ask for a name and put the file under the cursor in that stack."""
        self._ask(
            STACK_PROMPT, answer=lambda name: self._on_file(name, apply=self._stacked)
        )

    # The one operation that needs no name, so it does not go through _ask.
    def action_remove_stack(self) -> None:
        """Take the file under the cursor out of whatever stack it sits in."""
        if (file := self._under_cursor()) is None:
            return
        self._stacks.remove(file.id)
        self._report(TOOK_OUT.format(path=file.relative_path))
        self._show_carried()

    def _ask(self, prompt: str, *, answer: Callable[[str | None], None]) -> None:
        if self._under_cursor() is not None:
            self.app.push_screen(NamePrompt(prompt), answer)

    def _on_file(self, name: str | None, *, apply: Operation) -> None:
        """Carry the operation out on the file under the cursor and report it.

        Every operation the screen offers ends the same way — say what
        happened, then redraw what the file now carries — so it is said once.
        A name the service rejects is reported in place of the outcome.
        """
        file = self._under_cursor()
        if name is None or file is None:
            return
        try:
            message = apply(file, name=name)
        except REJECTIONS as error:
            message = str(error)
        self._report(message)
        self._show_carried()

    def _marked(self, file: FileDTO, *, name: str) -> str:
        mark = self._marks.add(file.id, name=name)
        return MARKED.format(path=file.relative_path, name=mark.name)

    def _took_off(self, file: FileDTO, *, name: str) -> str:
        self._marks.remove(file.id, name=name)
        return TOOK_OFF.format(name=name.strip(), path=file.relative_path)

    def _stacked(self, file: FileDTO, *, name: str) -> str:
        stack = self._stacks.add(file.id, name=name)
        return STACKED.format(path=file.relative_path, name=stack.name)

    def _under_cursor(self) -> FileDTO | None:
        table = self.query_one("#files", DataTable)
        if not self._shown or not 0 <= table.cursor_row < len(self._shown):
            return None
        return self._shown[table.cursor_row]

    def _report(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

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
        by_id = self._named[ROOTS]
        self._shown = self._files.list_all(self._scope)

        table = self.query_one("#files", DataTable)
        fill_table(
            table,
            columns=("Root", "Path", "Size"),
            rows=[
                (
                    by_id.get(file.root_id, UNKNOWN),
                    str(file.relative_path),
                    str(file.size),
                )
                for file in self._shown
            ],
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
                roots=ALL_ROOTS if root_id is None else by_id.get(root_id, UNKNOWN),
                marks=self._scope_label(
                    self._scope.mark_id,
                    names=self._named[MARKS],
                    any_label=ANY_MARK,
                    bare_label=UNMARKED,
                ),
                stacks=self._scope_label(
                    self._scope.stack_id,
                    names=self._named[STACKS],
                    any_label=ANY_STACK,
                    bare_label=UNSTACKED_ONLY,
                ),
            )
        )
        self._show_carried()

    @staticmethod
    def _scope_label(
        scope: Narrowing, *, names: dict[int, str], any_label: str, bare_label: str
    ) -> str:
        """Return the word describing one narrowing on the filter line.

        Returns:
            The label to show for this axis.
        """
        match scope:
            case None:
                return any_label
            case Bare.BARE:
                return bare_label
            case chosen:
                return names.get(chosen, UNKNOWN)
