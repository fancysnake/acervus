"""The root repository, backing the pacts protocol with SQLAlchemy."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from acervus.links.db.sqlalchemy.models import Root
from acervus.pacts.root import (
    RootDTO,
    RootNotFoundError,
    RootRepositoryProtocol,
    RootWrite,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session


class RootRepository(RootRepositoryProtocol):
    """Reads and writes roots in the index.

    Writes are flushed, never committed: the transaction boundary belongs to
    the service that opened it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[RootDTO]:
        """Return every root in the index.

        Returns:
            Every root, ordered by alias.
        """
        records = self._session.scalars(select(Root).order_by(Root.alias)).all()
        return [RootDTO.model_validate(record) for record in records]

    def read_by_alias(self, alias: str) -> RootDTO:
        """Return the root with this alias.

        Returns:
            The root holding this alias.

        Raises:
            RootNotFoundError: No root has this alias.
        """
        record = self._session.scalar(select(Root).where(Root.alias == alias))
        if record is None:
            message = f"No root is aliased {alias!r}."
            raise RootNotFoundError(message)
        return RootDTO.model_validate(record)

    def upsert_many(self, roots: Iterable[RootWrite]) -> list[RootDTO]:
        """Insert or update roots by alias.

        Returns:
            The written roots, in the order they were given.
        """
        wanted = list(roots)
        standing = {
            record.alias: record
            for record in self._session.scalars(
                select(Root).where(Root.alias.in_([root["alias"] for root in wanted]))
            ).all()
        }
        written = []
        for root in wanted:
            if (record := standing.get(root["alias"])) is None:
                record = Root(alias=root["alias"], path=str(root["path"]))
                self._session.add(record)
                standing[root["alias"]] = record
            else:
                record.path = str(root["path"])
            written.append(record)
        self._session.flush()
        return [RootDTO.model_validate(record) for record in written]

    def delete_many(self, aliases: Iterable[str]) -> None:
        """Delete the roots with these aliases, along with their files."""
        # Deleted one instance at a time rather than with a bulk DELETE: the
        # files relationship cascades delete-orphan, which SQLAlchemy applies
        # per instance. A bulk statement would leave the file rows behind.
        records = self._session.scalars(
            select(Root).where(Root.alias.in_(list(aliases)))
        ).all()
        for record in records:
            self._session.delete(record)
        self._session.flush()
