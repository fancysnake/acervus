"""The database container: engine, session, repositories and the transaction."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import (
    FileRepository,
    MarkRepository,
    RootRepository,
    SessionTransaction,
    StackRepository,
)
from acervus.links.db.sqlalchemy.engine import create_engine_from_path, init_db

if TYPE_CHECKING:
    from pathlib import Path


class Repositories:
    """Opens the database once and hands out repositories over one session.

    Every repository shares the session the transaction commits, so a service
    holding both writes through a single boundary.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @cached_property
    def session(self) -> Session:
        """Return the session every repository here shares, creating the database."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine_from_path(self._db_path)
        init_db(engine)
        return Session(engine)

    @cached_property
    def roots(self) -> RootRepository:
        """Return the root repository."""
        return RootRepository(self.session)

    @cached_property
    def files(self) -> FileRepository:
        """Return the file repository."""
        return FileRepository(self.session)

    @cached_property
    def marks(self) -> MarkRepository:
        """Return the mark repository."""
        return MarkRepository(self.session)

    @cached_property
    def stacks(self) -> StackRepository:
        """Return the stack repository."""
        return StackRepository(self.session)

    @cached_property
    def transaction(self) -> SessionTransaction:
        """Return the transaction boundary over the shared session."""
        return SessionTransaction(self.session)
