"""The file repository, backing the pacts protocol with SQLAlchemy."""

from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.sqlite import insert

from acervus.links.db.sqlalchemy.models import File, FileMark
from acervus.pacts.file import (
    Bare,
    FileDTO,
    FileFilter,
    FileRepositoryProtocol,
    FileWrite,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session


class _FileRow(TypedDict):
    """One row as the upsert statement takes it, with the path as a string."""

    root_id: int
    relative_path: str
    size: int
    mtime: float


def _carrying(mark_id: int | Bare) -> ColumnElement[bool]:
    """Return the clause keeping files that carry this mark, or carry none.

    Returns:
        A boolean clause over ``File``.
    """
    carried = select(FileMark).where(FileMark.file_id == File.id)
    if mark_id is Bare.BARE:
        return ~carried.exists()
    return carried.where(FileMark.mark_id == mark_id).exists()


def _sitting_in(stack_id: int | Bare) -> ColumnElement[bool]:
    """Return the clause keeping files in this stack, or in none at all.

    Returns:
        A boolean clause over ``File``.
    """
    if stack_id is Bare.BARE:
        return File.stack_id.is_(None)
    return File.stack_id == stack_id


class FileRepository(FileRepositoryProtocol):
    """Reads and writes files in the index.

    Writes are flushed, never committed: the transaction boundary belongs to
    the service that opened it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self, scope: FileFilter | None = None) -> list[FileDTO]:
        """Return indexed files, narrowed by the filter when one is given.

        Returns:
            The matching files, ordered by root and then relative path.
        """
        narrowed = scope or FileFilter()
        statement = select(File).order_by(File.root_id, File.relative_path)
        if narrowed.root_id is not None:
            statement = statement.where(File.root_id == narrowed.root_id)
        if narrowed.mark_id is not None:
            statement = statement.where(_carrying(narrowed.mark_id))
        if narrowed.stack_id is not None:
            statement = statement.where(_sitting_in(narrowed.stack_id))
        return [
            FileDTO.model_validate(record)
            for record in self._session.scalars(statement).all()
        ]

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
        wanted: list[_FileRow] = [
            {
                "root_id": file["root_id"],
                "relative_path": str(file["relative_path"]),
                "size": file["size"],
                "mtime": file["mtime"],
            }
            for file in files
        ]
        if not wanted:
            return []
        upsert = insert(File)
        self._session.execute(
            upsert.on_conflict_do_update(
                index_elements=[File.root_id, File.relative_path],
                set_={"size": upsert.excluded.size, "mtime": upsert.excluded.mtime},
            ),
            wanted,
        )
        self._session.flush()
        return [FileDTO.model_validate(record) for record in self._read(wanted)]

    def _read(self, wanted: list[_FileRow]) -> list[File]:
        """Return the written files in the order they were given.

        Returns:
            One record per wanted root and relative path.
        """
        keys = [(file["root_id"], file["relative_path"]) for file in wanted]
        # populate_existing: the upsert went round the session, so a record it
        # changed is still in the identity map holding the size it had before.
        written = {
            (record.root_id, record.relative_path): record
            for record in self._session.scalars(
                select(File)
                .where(tuple_(File.root_id, File.relative_path).in_(keys))
                .execution_options(populate_existing=True)
            ).all()
        }
        return [written[key] for key in keys]

    def delete_many(self, file_ids: Iterable[int]) -> None:
        """Delete the files with these ids."""
        self._session.execute(delete(File).where(File.id.in_(list(file_ids))))
        self._session.flush()
        # The database cascaded the file_marks rows away without telling the
        # session, so anything it still holds from before is out of date.
        self._session.expire_all()
