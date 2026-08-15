"""The files screen — lists the files Acervus has indexed, and marks them."""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, ClassVar, override

from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.prompt import NamePrompt
from acervus.gates.tui.textual.table import append_rows, fill_table
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
COLUMNS = ("", "Root", "Path", "Size")  # the first column carries the selection mark
PICKED = "•"
UNPICKED = " "
PICKED_COUNT = "{count} selected."
PICKED_NONE = "Nothing selected."
ADD_PROMPT = "Mark to add:"
REMOVE_PROMPT = "Mark to remove:"
MARKED = "Marked {path} {name}."
MARKED_MANY = "Marked {count} files {name}."
TOOK_OFF = "Took {name} off {path}."
TOOK_OFF_MANY = "Took {name} off {count} files."
CARRIES = "Marks: {names}"
CARRIES_NONE = "Marks: none"
STACK_PROMPT = "Stack to put it in:"
SITS_IN = "Stack: {name}"
SITS_LOOSE = "Stack: none"
STACKED = "Put {path} in {name}."
STACKED_MANY = "Put {count} files in {name}."
TOOK_OUT = "Took {path} out of its stack."
TOOK_OUT_MANY = "Took {count} files out of their stacks."
PARTLY = "{name}: {done} of {count} files."
REJECTIONS = (InvalidMarkNameError, InvalidStackNameError, MarkNotFoundError)

# The listing is read a page at a time: a root can hold hundreds of thousands
# of files, and reading every one of them before the first row can be drawn is
# a wait long enough to look like a hang. A page is far more than a terminal
# shows, and the next one is read once the cursor comes within sight of the end.
PAGE = 200
LOOKAHEAD = 20

# One thing the screen does to one file, returning the name it settled on.
type Deed = Callable[[FileDTO], str]


@dataclass(slots=True)
class Listing:
    """How much of the file list is on screen, and what is picked out of it.

    The three move together: a filter step throws all of them away at once,
    because the rows it reads are not the rows that were picked.
    """

    shown: list[FileDTO] = field(default_factory=list)
    drained: bool = False  # whether the last page of the listing is in
    # Keyed by id, so a file stays picked when the row it sits on is redrawn.
    picked: dict[int, FileDTO] = field(default_factory=dict)


class FilesScreen(Screen[None]):
    """Shows indexed files, filterable by root, and marks the ones selected."""

    BINDINGS: ClassVar[list[BindingType]] = [
        # The filter keys take a consonant from the noun: mar(k), sta(c)k.
        ("r", "cycle_filter", "Filter by root"),
        ("k", "cycle_mark", "Filter by mark"),
        ("c", "cycle_stack", "Filter by stack"),
        ("space", "toggle_selected", "Select"),
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
        self._listing = Listing()
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
        """Read further ahead if need be, and show what the cursor has reached."""
        self._reach_ahead()
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

    def action_toggle_selected(self) -> None:
        """Take the file under the cursor into the selection, or out of it.

        With nothing selected the operations are aimed at the file under the
        cursor, so a selection of one is worth making: it is how the same
        operation reaches a file the cursor has since left.
        """
        table = self.query_one("#files", DataTable)
        if (file := self._under_cursor()) is None:
            return
        picked = self._listing.picked
        if picked.pop(file.id, None) is None:
            picked[file.id] = file
        table.update_cell_at(
            Coordinate(table.cursor_row, 0), PICKED if file.id in picked else UNPICKED
        )
        self._report(PICKED_COUNT.format(count=len(picked)) if picked else PICKED_NONE)

    def action_add_mark(self) -> None:
        """Ask for a name and put that mark on every file aimed at."""
        self._ask(ADD_PROMPT, under=self._marking, one=MARKED, many=MARKED_MANY)

    def action_remove_mark(self) -> None:
        """Ask for a name and take that mark off every file aimed at."""
        self._ask(
            REMOVE_PROMPT, under=self._unmarking, one=TOOK_OFF, many=TOOK_OFF_MANY
        )

    def action_add_stack(self) -> None:
        """Ask for a name and put every file aimed at in that stack."""
        self._ask(STACK_PROMPT, under=self._stacking, one=STACKED, many=STACKED_MANY)

    # The one operation that needs no name, so it does not go through _ask.
    def action_remove_stack(self) -> None:
        """Take every file aimed at out of whatever stack it sits in."""
        self._carry_out(self._took_out, one=TOOK_OUT, many=TOOK_OUT_MANY)

    def _ask(
        self, prompt: str, *, under: Callable[[str], Deed], one: str, many: str
    ) -> None:
        """Ask for a name, then carry out under it what the name was for."""

        def answered(name: str | None) -> None:
            if name is not None:
                self._carry_out(under(name), one=one, many=many)

        if self._aimed_at():
            self.app.push_screen(NamePrompt(prompt), answered)

    def _aimed_at(self) -> list[FileDTO]:
        """Return the files an operation is to be carried out on.

        A selection is what the operations are aimed at; with nothing selected
        they are aimed at the file under the cursor, so the screen works the
        same whether or not anything has been picked.

        Returns:
            The selected files, or the one under the cursor, or none at all.
        """
        if self._listing.picked:
            return list(self._listing.picked.values())
        file = self._under_cursor()
        return [] if file is None else [file]

    def _carry_out(self, deed: Deed, *, one: str, many: str) -> None:
        """Carry the deed out on every file aimed at and report what happened.

        Every operation the screen offers ends the same way — say what
        happened, then redraw what the file under the cursor now carries — so
        it is said once. A refusal stops that file and no other: taking a mark
        off a selection is refused for the files not carrying it, and the ones
        that were carrying it are done all the same.
        """
        if not (files := self._aimed_at()):
            return
        done: list[str] = []
        refused: str | None = None
        for file in files:
            try:
                done.append(deed(file))
            except REJECTIONS as error:
                refused = refused or str(error)
        self._report(
            self._outcome(files, done=done, refused=refused, one=one, many=many)
        )
        self._show_carried()

    @staticmethod
    def _outcome(
        files: list[FileDTO],
        *,
        done: list[str],
        refused: str | None,
        one: str,
        many: str,
    ) -> str:
        """Return what to say about a deed carried out on these files.

        Returns:
            The refusal if nothing was done, how far it got if it was refused
            part of the way, and the outcome if it reached every file.
        """
        if not done:
            return refused or ""
        if len(done) < len(files):
            return PARTLY.format(name=done[0], done=len(done), count=len(files))
        if len(files) == 1:
            return one.format(path=files[0].relative_path, name=done[0])
        return many.format(count=len(files), name=done[0])

    def _marking(self, name: str) -> Deed:
        """Return what puts a mark of this name on a file.

        Returns:
            A deed answering with the name of the mark the file now carries.
        """
        return lambda file: self._marks.add(file.id, name=name).name

    def _unmarking(self, name: str) -> Deed:
        """Return what takes the mark of this name off a file.

        Returns:
            A deed answering with the name of the mark that was taken off.
        """

        def took_off(file: FileDTO) -> str:
            self._marks.remove(file.id, name=name)
            return name.strip()

        return took_off

    def _stacking(self, name: str) -> Deed:
        """Return what puts a file in the stack of this name.

        Returns:
            A deed answering with the name of the stack the file now sits in.
        """
        return lambda file: self._stacks.add(file.id, name=name).name

    def _took_out(self, file: FileDTO) -> str:
        """Take this file out of whatever stack it sits in.

        Returns:
            No name — what this one reports names no stack.
        """
        self._stacks.remove(file.id)
        return ""

    def _under_cursor(self) -> FileDTO | None:
        table = self.query_one("#files", DataTable)
        shown = self._listing.shown
        if not shown or not 0 <= table.cursor_row < len(shown):
            return None
        return shown[table.cursor_row]

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
        """Read the listing again from its first page.

        The filter decides which files there are, so moving it puts different
        files on the rows — and the selection, which is a set of files rather
        than of rows, goes with them.
        """
        self._listing = Listing()
        table = self.query_one("#files", DataTable)
        fill_table(table, columns=COLUMNS, rows=())
        self._load_page()

        drawn = bool(self._listing.shown)
        table.display = drawn
        empty = self.query_one("#no-files", Static)
        empty.display = not drawn
        empty.update(
            NO_FILES_MESSAGE if self._scope == FileFilter() else NO_MATCHES_MESSAGE
        )
        by_id = self._named[ROOTS]
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

    def _reach_ahead(self) -> None:
        """Read the next page once the cursor comes within sight of the end."""
        row = self.query_one("#files", DataTable).cursor_row
        if not self._listing.drained and row >= len(self._listing.shown) - LOOKAHEAD:
            self._load_page()

    def _load_page(self) -> None:
        """Read the page after the rows already shown and put it under them."""
        shown = self._listing.shown
        page = self._files.list_all(self._scope, limit=PAGE, offset=len(shown))
        self._listing.drained = len(page) < PAGE
        shown.extend(page)
        append_rows(
            self.query_one("#files", DataTable), rows=[self._row(file) for file in page]
        )

    def _row(self, file: FileDTO) -> tuple[str, str, str, str]:
        """Return the cells a file takes up on one row.

        Returns:
            The selection mark, the root's alias, the path and the size.
        """
        return (
            PICKED if file.id in self._listing.picked else UNPICKED,
            self._named[ROOTS].get(file.root_id, UNKNOWN),
            str(file.relative_path),
            str(file.size),
        )

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
