"""Public surface of the SQLAlchemy database adapter.

Models, the declarative base, and the engine stay internal — callers outside
``links`` reach this adapter only through the repository protocols in
``pacts``.
"""

from acervus.links.db.sqlalchemy.repositories import FileRepository, RootRepository

__all__ = ["FileRepository", "RootRepository"]
