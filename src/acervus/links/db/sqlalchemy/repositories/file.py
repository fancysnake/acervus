"""The file repository, backing the pacts protocol with SQLAlchemy."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from acervus.links.db.sqlalchemy.models import File, FileMark, Mark, Stack
from acervus.pacts.file import FileDTO, FileFilter, FileRepositoryProtocol, FileWrite

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session


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
        if narrowed.mark is not None:
            statement = statement.where(
                select(FileMark)
                .join(Mark, Mark.id == FileMark.mark_id)
                .where(FileMark.file_id == File.id, Mark.name == narrowed.mark)
                .exists()
            )
        if narrowed.unmarked:
            statement = statement.where(
                ~select(FileMark).where(FileMark.file_id == File.id).exists()
            )
        if narrowed.stack is not None:
            statement = statement.where(
                select(Stack)
                .where(Stack.id == File.stack_id, Stack.name == narrowed.stack)
                .exists()
            )
        if narrowed.unstacked:
            statement = statement.where(File.stack_id.is_(None))
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
