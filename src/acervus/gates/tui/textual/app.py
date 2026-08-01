"""Textual TUI application — interactive browser for Acervus."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App

from acervus.gates.tui.textual.files import FilesScreen
from acervus.gates.tui.textual.roots import RootsScreen

if TYPE_CHECKING:
    from textual.binding import BindingType

    from acervus.pacts.file import FileServiceProtocol, ScanServiceProtocol
    from acervus.pacts.root import RootServiceProtocol


class AcervusApp(App[None]):
    """Interactive browser for the index.

    Takes the service protocols its screens need and nothing more — no
    container and no configuration cross this boundary.
    """

    TITLE = "Acervus"
    BINDINGS: ClassVar[list[BindingType]] = [
        ("f", "files", "Files"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        roots: RootServiceProtocol,
        scan: ScanServiceProtocol,
        files: FileServiceProtocol,
    ) -> None:
        super().__init__()
        self._roots = roots
        self._scan = scan
        self._files = files

    def get_default_screen(self) -> RootsScreen:
        return RootsScreen(self._roots, self._scan)

    async def action_files(self) -> None:
        """Open the files screen, waiting for it to mount."""
        await self.push_screen(FilesScreen(self._roots, self._files))
