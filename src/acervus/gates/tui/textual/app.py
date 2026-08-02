"""Textual TUI application — interactive browser for Acervus."""

from typing import TYPE_CHECKING, ClassVar

from textual.app import App

from acervus.gates.tui.textual.files import FilesScreen
from acervus.gates.tui.textual.marks import MarksScreen
from acervus.gates.tui.textual.roots import RootsScreen
from acervus.gates.tui.textual.stacks import StacksScreen

if TYPE_CHECKING:
    from textual.binding import BindingType

    from acervus.pacts.file import FileServiceProtocol, ScanServiceProtocol
    from acervus.pacts.mark import MarkServiceProtocol
    from acervus.pacts.root import RootServiceProtocol
    from acervus.pacts.stack import StackServiceProtocol


class AcervusApp(App[None]):
    """Interactive browser for the index.

    Takes the service protocols its screens need and nothing more — no
    container and no configuration cross this boundary.
    """

    TITLE = "Acervus"
    BINDINGS: ClassVar[list[BindingType]] = [
        ("f", "files", "Files"),
        ("m", "marks", "Marks"),
        ("t", "stacks", "Stacks"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        roots: RootServiceProtocol,
        scan: ScanServiceProtocol,
        files: FileServiceProtocol,
        marks: MarkServiceProtocol,
        stacks: StackServiceProtocol,
    ) -> None:
        super().__init__()
        self._roots = roots
        self._scan = scan
        self._files = files
        self._marks = marks
        self._stacks = stacks

    def get_default_screen(self) -> RootsScreen:
        return RootsScreen(roots=self._roots, scan=self._scan)

    async def action_files(self) -> None:
        """Open the files screen, waiting for it to mount."""
        await self.push_screen(
            FilesScreen(
                roots=self._roots,
                files=self._files,
                marks=self._marks,
                stacks=self._stacks,
            )
        )

    async def action_marks(self) -> None:
        """Open the marks screen, waiting for it to mount."""
        await self.push_screen(MarksScreen(self._marks))

    async def action_stacks(self) -> None:
        """Open the stacks screen, waiting for it to mount."""
        await self.push_screen(StacksScreen(stacks=self._stacks, files=self._files))
