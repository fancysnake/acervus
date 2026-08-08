"""Opening the SQLite file the index lives in."""

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from acervus.links.db.sqlalchemy.models import Base

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine


def open_database(db_path: Path) -> Engine:
    """Open the database at this path, creating the file and its tables.

    Returns:
        An engine over the SQLite file, ready for sessions.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine
