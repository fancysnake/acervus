"""The transaction boundary over a SQLAlchemy session."""

from __future__ import annotations

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
        """Commit the session on a clean exit, roll it back on an exception.

        Yields:
            Control to the caller, whose writes commit together.
        """
        try:
            yield
        except Exception:
            self._session.rollback()
            raise
        self._session.commit()
