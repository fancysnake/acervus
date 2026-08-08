"""The database container: engine, session, repositories and the transaction."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import (
    FileRepository,
    MarkRepository,
    RootRepository,
    SessionTransaction,
    StackRepository,
)
from acervus.links.db.sqlalchemy.engine import open_database

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine


class Repositories:
    """Opens the database once and hands out repositories over one session.

    Every repository shares the session the transaction commits, so a service
    holding both writes through a single boundary.

    The caller owns the database handle: close it, or the SQLite connection the
    engine pools stays open until the garbage collector finalizes it.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._engine: Engine | None = None
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        """Return the session every repository here shares, creating the database."""
        if self._session is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._engine = open_database(self._db_path)
            self._session = Session(self._engine)
        return self._session

    def apart(self) -> Repositories:
        """Return a second container over the same database, on its own session.

        A SQLAlchemy session belongs to one thread, so work that runs off the
        interface thread gets a container of its own rather than sharing this
        one. The caller owns it, and closes it when the work is done.

        Returns:
            A container over the same database file, opened separately.
        """
        return Repositories(self._db_path)

    def close(self) -> None:
        """Close the session and dispose the engine, releasing the SQLite handle.

        Whether the session is open is the only thing tracked, so closing an
        unused container does not create the database it never touched, a
        second close does nothing, and a container used again reopens.
        """
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    @property
    def roots(self) -> RootRepository:
        """Return the root repository."""
        return RootRepository(self.session)

    @property
    def files(self) -> FileRepository:
        """Return the file repository."""
        return FileRepository(self.session)

    @property
    def marks(self) -> MarkRepository:
        """Return the mark repository."""
        return MarkRepository(self.session)

    @property
    def stacks(self) -> StackRepository:
        """Return the stack repository."""
        return StackRepository(self.session)

    @property
    def transaction(self) -> SessionTransaction:
        """Return the transaction boundary over the shared session."""
        return SessionTransaction(self.session)
