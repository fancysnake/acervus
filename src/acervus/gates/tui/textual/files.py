"""The files screen — browses the indexed files by directory, and marks them."""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, override

from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from acervus.gates.tui.textual.prompt import NamePrompt
from acervus.gates.tui.textual.table import append_rows, fill_table
from acervus.pacts.file import BARE, Bare, FileFilter
from acervus.pacts.mark import InvalidMarkNameError, MarkNotFoundError
from acervus.pacts.stack import InvalidStackNameError, StackFileNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from textual.app import ComposeResult
    from textual.binding import BindingType

    from acervus.pacts.file import (
        DirectorySummary,
        FileDTO,
        FileRepositoryProtocol,
        Narrowing,
    )
    from acervus.pacts.mark import MarkServiceProtocol
    from acervus.pacts.root import RootServiceProtocol
    from acervus.pacts.stack import StackServiceProtocol

NO_ROOTS_MESSAGE = "No roots configured."
NO_FILES_MESSAGE = "No files indexed. Scan a root first."
NO_MATCHES_MESSAGE = "No files match this filter."
ANY_MARK = "any mark"
UNMARKED = "unmarked"
ANY_STACK = "any stack"
UNSTACKED_ONLY = "unstacked"
FILTER_LABEL = "Showing: {where}, {marks}, {stacks}"
WHERE_DEEPER = "{alias} > {directory}"
UNKNOWN = "?"  # a root, mark or stack the screen has no name for
ROOTS = "roots"
MARKS = "marks"
STACKS = "stacks"
COLUMNS = ("", "Name", "Files", "Size")  # the first column carries the selection
UP = ".."  # the row that leads out of the directory being browsed
FOLDER = "{name}/"  # how a directory is told apart from a file at a glance
PICKED = "•"
UNPICKED = " "
NOTHING = ""
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
REJECTIONS = (
    InvalidMarkNameError,
    InvalidStackNameError,
    MarkNotFoundError,
    # A scan running on its own thread can delete a file the rows still show.
    StackFileNotFoundError,
)
TOP = Path()  # the directory a root is browsed from

# A directory's own files are read a page at a time: one can hold hundreds of
# thousands, and reading every one of them before the first row can be drawn is
# a wait long enough to look like a hang. A page is far more than a terminal
# shows, and the next one is read once the cursor comes within sight of the end.
PAGE = 200
LOOKAHEAD = 20

# One thing the screen does to one file, returning the name it settled on.
type Deed = Callable[[FileDTO], str]


@dataclass(slots=True)
class Listing:
    """What one directory puts on the rows, and what is picked out of it.

    The rows run in the order they are read: the way up, then the directories,
    then as much of the directory's own files as has been read. They move
    together, because moving anywhere throws all of them away at once.
    """

    ascends: bool = False  # whether the first row leads out of this directory
    directories: list[DirectorySummary] = field(default_factory=list)
    shown: list[FileDTO] = field(default_factory=list)
    drained: bool = False  # whether the last page of the files is in
    # Keyed by id, so a file stays picked when the row it sits on is redrawn.
    picked: dict[int, FileDTO] = field(default_factory=dict)

    @property
    def above(self) -> int:
        """How many rows come before the first file."""
        return int(self.ascends) + len(self.directories)

    @property
    def rows(self) -> int:
        """How many rows the listing puts on the table."""
        return self.above + len(self.shown)

    def file_at(self, row: int) -> FileDTO | None:
        """Return the file this row shows, if it shows one.

        Returns:
            The file, or ``None`` where the row is the way up or a directory.
        """
        index = row - self.above
        return self.shown[index] if 0 <= index < len(self.shown) else None

    def directory_at(self, row: int) -> DirectorySummary | None:
        """Return the directory this row shows, if it shows one.

        Returns:
            The directory, or ``None`` where the row is the way up or a file.
        """
        index = row - int(self.ascends)
        return self.directories[index] if 0 <= index < len(self.directories) else None

    def is_way_up(self, row: int) -> bool:
        """Say whether this row is the one leading out of the directory.

        Returns:
            Whether the row leads up.
        """
        return self.ascends and row == 0


class FilesScreen(Screen[None]):
    """Browses one directory of one root, and marks the files selected in it."""

    BINDINGS: ClassVar[list[BindingType]] = [
        # The table binds enter itself, so the screen has to claim it first.
        Binding("enter", "descend", "Open", priority=True),
        ("backspace", "ascend", "Up"),
        # The filter keys take a consonant from the noun: mar(k), sta(c)k.
        ("r", "cycle_root", "Next root"),
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
        # Where the screen is: one root, one directory inside it, and whatever
        # the mark and stack filters narrow that directory to.
        self._scope = FileFilter(directory=TOP)
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
        named = self._named[ROOTS] = {
            root.id: root.alias for root in self._roots.list_all()
        }
        # The screen is always inside one root, so it opens in the first.
        self._scope = replace(self._scope, root_id=next(iter(named), None))
        self._refresh()

    def on_data_table_row_highlighted(self) -> None:
        """Read further ahead if need be, and show what the cursor has reached."""
        self._reach_ahead()
        self._show_carried()

    def action_descend(self) -> None:
        """Open the directory under the cursor, or go up where that row leads."""
        row = self.query_one("#files", DataTable).cursor_row
        if self._listing.is_way_up(row):
            self.action_ascend()
            return
        if (directory := self._listing.directory_at(row)) is not None:
            self._go(self._where() / directory.name)

    def action_ascend(self) -> None:
        """Leave this directory for the one holding it, if there is one."""
        if (here := self._where()) != TOP:
            self._go(here.parent, land_on=here.name)

    def _where(self) -> Path:
        """Return the directory being browsed.

        Returns:
            The path within the root, ``Path()`` at the top of it.
        """
        return self._scope.directory or TOP

    def _go(self, directory: Path, *, land_on: str | None = None) -> None:
        """Browse this directory, leaving the cursor on the row named."""
        self._scope = replace(self._scope, directory=directory)
        self._refresh(land_on=land_on)

    def action_cycle_root(self) -> None:
        """Step on to the next root, wrapping round, at the top of it."""
        named = self._named[ROOTS] = {
            root.id: root.alias for root in self._roots.list_all()
        }
        if not named:
            return
        # No unfiltered step: the screen is always inside exactly one root.
        steps: list[int | None] = list(named)
        self._scope = replace(
            self._scope, root_id=self._next(steps, self._scope.root_id), directory=TOP
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

        Only files are selected. A directory row is not a target, so no key
        here reaches every file in a directory at once.
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
        same whether or not anything has been picked. A cursor sitting on a
        directory is aimed at nothing at all.

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
            return refused or NOTHING
        if len(done) < len(files):
            return PARTLY.format(name=done[0], done=len(done), count=len(files))
        if len(files) == 1:
            return one.format(path=files[0].relative_path.name, name=done[0])
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
        return NOTHING

    def _under_cursor(self) -> FileDTO | None:
        table = self.query_one("#files", DataTable)
        return self._listing.file_at(table.cursor_row)

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

    def _refresh(self, *, land_on: str | None = None) -> None:
        """Read this directory again, from its first page of files.

        Everything on the rows belongs to where the screen is, so moving
        anywhere reads the lot again — and the selection, which is a set of
        files rather than of rows, goes with it.
        """
        here = self._where()
        self._listing = Listing(ascends=here != TOP)
        self._listing.directories = (
            []
            if self._scope.root_id is None
            else self._files.list_directories(self._scope)
        )
        table = self.query_one("#files", DataTable)
        fill_table(table, columns=COLUMNS, rows=self._standing_rows())
        self._load_page()

        table.display = bool(self._listing.rows)
        empty = self.query_one("#no-files", Static)
        empty.display = not self._listing.directories and not self._listing.shown
        empty.update(self._empty_message())
        self._show_where()
        if land_on is not None:
            self._land_on(land_on)
        self._show_carried()

    def _standing_rows(self) -> list[tuple[str, str, str, str]]:
        """Return the rows above the files: the way up, then the directories.

        Returns:
            One row per row that is not a file.
        """
        rows = [(UNPICKED, UP, NOTHING, NOTHING)] if self._listing.ascends else []
        return rows + [
            (
                UNPICKED,
                FOLDER.format(name=directory.name),
                str(directory.file_count),
                NOTHING,
            )
            for directory in self._listing.directories
        ]

    def _land_on(self, name: str) -> None:
        """Put the cursor on the directory of this name, if it is on a row."""
        for index, directory in enumerate(self._listing.directories):
            if directory.name == name:
                self.query_one("#files", DataTable).move_cursor(
                    row=index + int(self._listing.ascends)
                )
                return

    def _empty_message(self) -> str:
        """Return what to say in place of an empty table.

        Returns:
            The reason there is nothing to show.
        """
        if self._scope.root_id is None:
            return NO_ROOTS_MESSAGE
        narrowed = self._scope.mark_id is not None or self._scope.stack_id is not None
        return NO_MATCHES_MESSAGE if narrowed else NO_FILES_MESSAGE

    def _show_where(self) -> None:
        """Say which directory of which root is on the rows, and how narrowed."""
        alias = self._named[ROOTS].get(self._scope.root_id or 0, UNKNOWN)
        here = self._where()
        self.query_one("#file-filter", Static).update(
            FILTER_LABEL.format(
                where=(
                    alias
                    if here == TOP
                    else WHERE_DEEPER.format(alias=alias, directory=here.as_posix())
                ),
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

    def _reach_ahead(self) -> None:
        """Read the next page once the cursor comes within sight of the end."""
        row = self.query_one("#files", DataTable).cursor_row
        if not self._listing.drained and row >= self._listing.rows - LOOKAHEAD:
            self._load_page()

    def _load_page(self) -> None:
        """Read the page after the files already shown and put it under them."""
        if self._scope.root_id is None:
            self._listing.drained = True
            return
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
            The selection mark, the file's name, no count, and its size.
        """
        return (
            PICKED if file.id in self._listing.picked else UNPICKED,
            file.relative_path.name,
            NOTHING,
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
