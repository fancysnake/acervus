"""The root repository, backing the pacts protocol with SQLAlchemy."""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert

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
        wanted = [{"alias": root["alias"], "path": str(root["path"])} for root in roots]
        if not wanted:
            return []
        upsert = insert(Root)
        self._session.execute(
            upsert.on_conflict_do_update(
                index_elements=[Root.alias], set_={"path": upsert.excluded.path}
            ),
            wanted,
        )
        self._session.flush()
        return [RootDTO.model_validate(record) for record in self._read(wanted)]

    def _read(self, wanted: list[dict[str, str]]) -> list[Root]:
        """Return the written roots in the order they were given.

        Returns:
            One record per wanted alias.
        """
        aliases = [root["alias"] for root in wanted]
        # populate_existing: the upsert went round the session, so a record it
        # changed is still in the identity map holding the path it had before.
        written = {
            record.alias: record
            for record in self._session.scalars(
                select(Root)
                .where(Root.alias.in_(aliases))
                .execution_options(populate_existing=True)
            ).all()
        }
        return [written[alias] for alias in aliases]

    def delete_many(self, aliases: Iterable[str]) -> None:
        """Delete the roots with these aliases, along with their files."""
        self._session.execute(delete(Root).where(Root.alias.in_(list(aliases))))
        self._session.flush()
        # The database cascaded the file rows away without telling the session,
        # so anything it still holds from before is no longer what is on disk.
        self._session.expire_all()
