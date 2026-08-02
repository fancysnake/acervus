"""The service container, flat: one property per service."""

from functools import cached_property
from typing import TYPE_CHECKING

from acervus.links.fs.pathlib import PathlibFilesystemReader
from acervus.mills.file import FileService, ScanService
from acervus.mills.mark import MarkService
from acervus.mills.root import RootService
from acervus.mills.stack import StackService

if TYPE_CHECKING:
    from acervus.inits.repositories import Repositories


class Services:
    """Builds each service over the repositories and transaction it asks for."""

    def __init__(self, repositories: Repositories) -> None:
        self._repositories = repositories

    @cached_property
    def roots(self) -> RootService:
        """Return the root service."""
        return RootService(
            roots=self._repositories.roots, transaction=self._repositories.transaction
        )

    @cached_property
    def files(self) -> FileService:
        """Return the file service."""
        return FileService(self._repositories.files)

    @cached_property
    def marks(self) -> MarkService:
        """Return the mark service."""
        return MarkService(
            marks=self._repositories.marks, transaction=self._repositories.transaction
        )

    @cached_property
    def stacks(self) -> StackService:
        """Return the stack service."""
        return StackService(
            stacks=self._repositories.stacks, transaction=self._repositories.transaction
        )

    @cached_property
    def scan(self) -> ScanService:
        """Return the scan service, reading the filesystem with pathlib."""
        return ScanService(
            files=self._repositories.files,
            roots=self._repositories.roots,
            filesystem=PathlibFilesystemReader(),
            transaction=self._repositories.transaction,
        )
