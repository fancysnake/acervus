"""Textual TUI application — interactive browser for Acervus."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App

from acervus.gates.tui.textual.roots import RootsScreen

if TYPE_CHECKING:
    from textual.binding import BindingType

    from acervus.pacts.file import ScanServiceProtocol
    from acervus.pacts.root import RootServiceProtocol


class AcervusApp(App[None]):
    """Interactive browser for the indexed roots.

    Takes the service protocols its screens need and nothing more — no
    container and no configuration cross this boundary.
    """

    TITLE = "Acervus"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, roots: RootServiceProtocol, scan: ScanServiceProtocol) -> None:
        super().__init__()
        self._roots = roots
        self._scan = scan

    def get_default_screen(self) -> RootsScreen:
        return RootsScreen(self._roots, self._scan)
