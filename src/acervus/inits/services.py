"""The service container, flat: one property per service."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from acervus.links.fs.pathlib import PathlibFilesystemReader
from acervus.mills.file import ScanService
from acervus.mills.root import RootService

if TYPE_CHECKING:
    from acervus.inits.repositories import Repositories


class Services:
    """Builds each service over the repositories and transaction it asks for."""

    def __init__(self, repositories: Repositories) -> None:
        self._repositories = repositories

    @cached_property
    def roots(self) -> RootService:
        """Return the root service."""
        return RootService(self._repositories.roots, self._repositories.transaction)

    @cached_property
    def scan(self) -> ScanService:
        """Return the scan service, reading the filesystem with pathlib."""
        return ScanService(
            self._repositories.files,
            self._repositories.roots,
            PathlibFilesystemReader(),
            self._repositories.transaction,
        )
