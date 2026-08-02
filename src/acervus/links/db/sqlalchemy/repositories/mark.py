"""The mark repository, backing the pacts protocol with SQLAlchemy."""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.sql.functions import count

from acervus.links.db.sqlalchemy.models import FileMark, Mark
from acervus.pacts.mark import (
    MarkDTO,
    MarkNotFoundError,
    MarkRepositoryProtocol,
    MarkSummary,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MarkRepository(MarkRepositoryProtocol):
    """Reads and writes marks, and the links between marks and files.

    Writes are flushed, never committed: the transaction boundary belongs to
    the service that opened it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[MarkSummary]:
        """Return every mark with its file count.

        Returns:
            Every mark, ordered by name. A mark nothing carries counts zero.
        """
        counted = (
            select(Mark.id, Mark.name, count(FileMark.file_id))
            .outerjoin(FileMark, FileMark.mark_id == Mark.id)
            .group_by(Mark.id, Mark.name)
            .order_by(Mark.name)
        )
        return [
            MarkSummary(id=mark_id, name=name, file_count=file_count)
            for mark_id, name, file_count in self._session.execute(counted).all()
        ]

    def list_for_file(self, file_id: int) -> list[MarkDTO]:
        """Return the marks this file carries.

        Returns:
            The file's marks, ordered by name.
        """
        carried = (
            select(Mark)
            .join(FileMark, FileMark.mark_id == Mark.id)
            .where(FileMark.file_id == file_id)
            .order_by(Mark.name)
        )
        return [
            MarkDTO.model_validate(record)
            for record in self._session.scalars(carried).all()
        ]

    def read_by_name(self, name: str) -> MarkDTO:
        """Return the mark with this name.

        Returns:
            The mark holding this name.

        Raises:
            MarkNotFoundError: No mark has this name.
        """
        record = self._session.scalar(select(Mark).where(Mark.name == name))
        if record is None:
            message = f"No mark is named {name!r}."
            raise MarkNotFoundError(message)
        return MarkDTO.model_validate(record)

    def create(self, name: str) -> MarkDTO:
        """Create a mark with this name.

        Returns:
            The mark just created, with the id it was given.
        """
        record = Mark(name=name)
        self._session.add(record)
        self._session.flush()
        return MarkDTO.model_validate(record)

    def attach(self, file_id: int, *, mark_id: int) -> None:
        """Put this mark on this file, doing nothing if it is already there."""
        if self._link(file_id, mark_id=mark_id) is None:
            self._session.add(FileMark(file_id=file_id, mark_id=mark_id))
            self._session.flush()

    def detach(self, file_id: int, *, mark_id: int) -> None:
        """Take this mark off this file, doing nothing if it is not there."""
        if (link := self._link(file_id, mark_id=mark_id)) is not None:
            self._session.delete(link)
            self._session.flush()

    def count_files(self, mark_id: int) -> int:
        """Return how many files carry this mark.

        Returns:
            The number of files linked to the mark.
        """
        counted = select(count(FileMark.file_id)).where(FileMark.mark_id == mark_id)
        return self._session.scalar(counted) or 0

    def delete(self, mark_id: int) -> None:
        """Delete this mark, detaching it from every file first."""
        self._session.execute(delete(FileMark).where(FileMark.mark_id == mark_id))
        if (record := self._session.get(Mark, mark_id)) is not None:
            self._session.delete(record)
        self._session.flush()

    def _link(self, file_id: int, *, mark_id: int) -> FileMark | None:
        return self._session.scalar(
            select(FileMark).where(
                FileMark.file_id == file_id, FileMark.mark_id == mark_id
            )
        )
