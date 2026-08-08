"""Opening the SQLite file the index lives in."""

from typing import TYPE_CHECKING

from sqlalchemy import create_engine, event

from acervus.links.db.sqlalchemy.models import Base

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine
    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.pool import ConnectionPoolEntry

# foreign_keys is off by default in SQLite, so every ondelete in the schema is
# inert until it is on. journal_mode leaves a reader from blocking the writer,
# which a scan running beside the interface depends on.
PRAGMAS = ("PRAGMA foreign_keys=ON", "PRAGMA journal_mode=WAL")


def open_database(db_path: Path) -> Engine:
    """Open the database at this path, creating the file and its tables.

    Returns:
        An engine over the SQLite file, enforcing the schema's foreign keys.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    event.listen(engine, "connect", _apply_pragmas)
    Base.metadata.create_all(engine)
    return engine


def _apply_pragmas(connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
    cursor = connection.cursor()
    for pragma in PRAGMAS:
        cursor.execute(pragma)
    cursor.close()
