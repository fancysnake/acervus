"""The transaction boundary over a SQLAlchemy session."""

from contextlib import contextmanager
from typing import TYPE_CHECKING

from acervus.pacts.transaction import TransactionProtocol

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.orm import Session


class SessionTransaction(TransactionProtocol):
    """Opens a transaction on the session the repositories share.

    Repositories flush but never commit, so every write a service makes lands
    on disk here or not at all.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @contextmanager
    def atomic(self) -> Iterator[None]:
        """Commit the session on a clean exit, roll it back on anything else.

        ``BaseException`` rather than ``Exception``: an interrupt or a
        cancelled worker would otherwise leave the flushed writes pending on
        the shared session, for the next block to commit as its own.

        The commit is guarded for the same reason. A commit that raises leaves
        the session inactive with its writes still pending, so a later block
        would either commit them or fail outright on a session nobody reset.

        Yields:
            Control to the caller, whose writes commit together.
        """
        try:
            yield
        except BaseException:
            self._session.rollback()
            raise
        try:
            self._session.commit()
        except BaseException:
            self._session.rollback()
            raise
