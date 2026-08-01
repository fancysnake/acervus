"""Repositories backing the pacts protocols with SQLAlchemy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.sql.functions import count

from acervus.links.db.sqlalchemy.models import File, FileMark, Mark, Root, Stack
from acervus.pacts.file import FileDTO, FileFilter, FileRepositoryProtocol, FileWrite
from acervus.pacts.mark import (
    MarkDTO,
    MarkNotFoundError,
    MarkRepositoryProtocol,
    MarkSummary,
)
from acervus.pacts.root import (
    RootDTO,
    RootNotFoundError,
    RootRepositoryProtocol,
    RootWrite,
)
from acervus.pacts.stack import (
    StackDTO,
    StackNotFoundError,
    StackRepositoryProtocol,
    StackSummary,
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

    def attach(self, file_id: int, mark_id: int) -> None:
        """Put this mark on this file, doing nothing if it is already there."""
        if self._link(file_id, mark_id) is None:
            self._session.add(FileMark(file_id=file_id, mark_id=mark_id))
            self._session.flush()

    def detach(self, file_id: int, mark_id: int) -> None:
        """Take this mark off this file, doing nothing if it is not there."""
        if (link := self._link(file_id, mark_id)) is not None:
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

    def _link(self, file_id: int, mark_id: int) -> FileMark | None:
        return self._session.scalar(
            select(FileMark).where(
                FileMark.file_id == file_id, FileMark.mark_id == mark_id
            )
        )


class StackRepository(StackRepositoryProtocol):
    """Reads and writes stacks, and which stack each file sits in.

    A file's stack is a column on the file, so a file sitting in two stacks is
    unrepresentable rather than merely forbidden.

    Writes are flushed, never committed: the transaction boundary belongs to
    the service that opened it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[StackSummary]:
        """Return every stack with its file count.

        Returns:
            Every stack, ordered by name. A stack holding nothing counts zero.
        """
        counted = (
            select(Stack.id, Stack.name, count(File.id))
            .outerjoin(File, File.stack_id == Stack.id)
            .group_by(Stack.id, Stack.name)
            .order_by(Stack.name)
        )
        return [
            StackSummary(id=stack_id, name=name, file_count=file_count)
            for stack_id, name, file_count in self._session.execute(counted).all()
        ]

    def read_by_name(self, name: str) -> StackDTO:
        """Return the stack with this name.

        Returns:
            The stack holding this name.

        Raises:
            StackNotFoundError: No stack has this name.
        """
        record = self._session.scalar(select(Stack).where(Stack.name == name))
        if record is None:
            message = f"No stack is named {name!r}."
            raise StackNotFoundError(message)
        return StackDTO.model_validate(record)

    def read_for_file(self, file_id: int) -> StackDTO | None:
        """Return the stack this file sits in.

        Returns:
            The file's stack, or ``None`` if it sits in none.
        """
        record = self._session.scalar(
            select(Stack)
            .join(File, File.stack_id == Stack.id)
            .where(File.id == file_id)
        )
        return None if record is None else StackDTO.model_validate(record)

    def create(self, name: str) -> StackDTO:
        """Create a stack with this name.

        Returns:
            The stack just created, with the id it was given.
        """
        record = Stack(name=name)
        self._session.add(record)
        self._session.flush()
        return StackDTO.model_validate(record)

    def set_for_file(self, file_id: int, stack_id: int | None) -> None:
        """Put this file in this stack, or take it out of any stack at ``None``."""
        if (record := self._session.get(File, file_id)) is not None:
            record.stack_id = stack_id
            self._session.flush()

    def count_files(self, stack_id: int) -> int:
        """Return how many files sit in this stack.

        Returns:
            The number of files whose stack is this one.
        """
        counted = select(count(File.id)).where(File.stack_id == stack_id)
        return self._session.scalar(counted) or 0

    def delete(self, stack_id: int) -> None:
        """Delete this stack, turning its files loose first."""
        for record in self._session.scalars(
            select(File).where(File.stack_id == stack_id)
        ).all():
            record.stack_id = None
        if (stack := self._session.get(Stack, stack_id)) is not None:
            self._session.delete(stack)
        self._session.flush()
