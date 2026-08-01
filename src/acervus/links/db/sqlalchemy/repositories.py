"""Repositories backing the pacts protocols with SQLAlchemy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from acervus.links.db.sqlalchemy.models import File, Root
from acervus.pacts.file import FileDTO, FileRepositoryProtocol, FileWrite
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

    def read(self, root_id: int) -> RootDTO:
        """Return the root with this id.

        Returns:
            The root holding this id.

        Raises:
            RootNotFoundError: No root has this id.
        """
        if (record := self._session.get(Root, root_id)) is None:
            message = f"No root has id {root_id}."
            raise RootNotFoundError(message)
        return RootDTO.model_validate(record)

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
        written = []
        for root in roots:
            record = self._session.scalar(
                select(Root).where(Root.alias == root["alias"])
            )
            if record is None:
                record = Root(alias=root["alias"], path=str(root["path"]))
                self._session.add(record)
            else:
                record.path = str(root["path"])
            written.append(record)
        self._session.flush()
        return [RootDTO.model_validate(record) for record in written]

    def delete_many(self, aliases: Iterable[str]) -> None:
        """Delete the roots with these aliases, along with their files."""
        records = self._session.scalars(
            select(Root).where(Root.alias.in_(list(aliases)))
        ).all()
        for record in records:
            self._session.delete(record)
        self._session.flush()


class FileRepository(FileRepositoryProtocol):
    """Reads and writes files in the index.

    Writes are flushed, never committed: the transaction boundary belongs to
    the service that opened it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_root(self, root_id: int) -> list[FileDTO]:
        """Return every indexed file under this root.

        Returns:
            Every file under the root, ordered by relative path.
        """
        records = self._session.scalars(
            select(File).where(File.root_id == root_id).order_by(File.relative_path)
        ).all()
        return [FileDTO.model_validate(record) for record in records]

    def upsert_many(self, files: Iterable[FileWrite]) -> list[FileDTO]:
        """Insert or update files by root and relative path.

        Returns:
            The written files, in the order they were given.
        """
        written = []
        for file in files:
            relative_path = str(file["relative_path"])
            record = self._session.scalar(
                select(File).where(
                    File.root_id == file["root_id"], File.relative_path == relative_path
                )
            )
            if record is None:
                record = File(
                    root_id=file["root_id"],
                    relative_path=relative_path,
                    size=file["size"],
                    mtime=file["mtime"],
                )
                self._session.add(record)
            else:
                record.size = file["size"]
                record.mtime = file["mtime"]
            written.append(record)
        self._session.flush()
        return [FileDTO.model_validate(record) for record in written]

    def delete_many(self, file_ids: Iterable[int]) -> None:
        """Delete the files with these ids."""
        records = self._session.scalars(
            select(File).where(File.id.in_(list(file_ids)))
        ).all()
        for record in records:
            self._session.delete(record)
        self._session.flush()
