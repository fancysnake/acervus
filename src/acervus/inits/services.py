"""The service container, flat: one property per service."""

from contextlib import closing
from functools import cached_property
from typing import TYPE_CHECKING

from acervus.links.fs.pathlib.reader import PathlibFilesystemReader
from acervus.mills.file import ScanService
from acervus.mills.mark import MarkService
from acervus.mills.root import RootService
from acervus.mills.stack import StackService
from acervus.pacts.file import ScanServiceProtocol

if TYPE_CHECKING:
    from collections.abc import Iterable

    from acervus.inits.repositories import Repositories
    from acervus.links.db.sqlalchemy import FileRepository
    from acervus.pacts.file import ScanResult


class IsolatedScan(ScanServiceProtocol):
    """Scans on a session of its own, so a scan can run off the caller's thread.

    A session belongs to one thread. Walking a large root takes long enough to
    be worth moving off the thread drawing the interface, which it can only be
    if it does not touch the session that thread is using.
    """

    def __init__(
        self, repositories: Repositories, *, ignore: Iterable[str] = ()
    ) -> None:
        self._repositories = repositories
        self._ignore = tuple(ignore)

    def scan(self, alias: str) -> ScanResult:
        """Walk the root with this alias and reconcile the index against it.

        Returns:
            How many files the index gained, lost and rewrote.
        """
        with closing(self._repositories.apart()) as apart:
            return ScanService(
                files=apart.files,
                roots=apart.roots,
                filesystem=PathlibFilesystemReader(self._ignore),
                transaction=apart.transaction,
            ).scan(alias)


class Services:
    """Builds each service over the repositories and transaction it asks for."""

    def __init__(
        self, repositories: Repositories, *, ignore: Iterable[str] = ()
    ) -> None:
        self._repositories = repositories
        self._ignore = tuple(ignore)

    @cached_property
    def roots(self) -> RootService:
        """The root service."""
        return RootService(
            roots=self._repositories.roots, transaction=self._repositories.transaction
        )

    # Reading files needs no business rule of its own, so there is no file
    # service to build: the screens read through the repository protocol.
    @cached_property
    def files(self) -> FileRepository:
        """The file repository the screens read through."""
        return self._repositories.files

    @cached_property
    def marks(self) -> MarkService:
        """The mark service."""
        return MarkService(
            marks=self._repositories.marks, transaction=self._repositories.transaction
        )

    @cached_property
    def stacks(self) -> StackService:
        """The stack service."""
        return StackService(
            stacks=self._repositories.stacks, transaction=self._repositories.transaction
        )

    @cached_property
    def scan(self) -> IsolatedScan:
        """The scan service, reading the filesystem with pathlib."""
        return IsolatedScan(self._repositories, ignore=self._ignore)
