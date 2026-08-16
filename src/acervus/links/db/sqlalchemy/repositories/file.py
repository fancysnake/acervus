"""The file repository, backing the pacts protocol with SQLAlchemy."""

from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.sql.functions import count

from acervus.links.db.sqlalchemy.models import File, FileMark
from acervus.pacts.file import (
    Bare,
    DirectorySummary,
    FileDTO,
    FileFilter,
    FileRepositoryProtocol,
    FileWrite,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

# Relative paths are written with the separator pathlib gives them, and the
# index is read on the platform that wrote it.
SEPARATOR = "/"


# SQLite compiles in a ceiling on how many parameters one statement may bind —
# 999 in builds before 3.32 — and a root holding thousands of files walks past
# it in a single scan. Every statement that spans files goes out in batches
# this wide, so the widest row here still fits: 200 files bind 800 parameters.
BATCH = 200


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


def _prefix(directory: Path | None) -> str:
    """Return what every path beneath this directory starts with.

    Returns:
        The directory and a separator, or nothing at the top of a root.
    """
    if directory is None or directory == Path():
        return ""
    return f"{directory.as_posix()}{SEPARATOR}"


def _beneath(prefix: str) -> list[ColumnElement[bool]]:
    """Return the clauses keeping the paths that start with this prefix.

    Written as a range rather than a ``LIKE``, so the index on root and
    relative path narrows the scan to the directory instead of reading the
    root out in full.

    Returns:
        Two boolean clauses over ``File``, or none at the top of a root.
    """
    if not prefix:
        return []
    # The separator is the last character, so the character after it bounds
    # every path the prefix can start.
    after = f"{prefix[:-1]}{chr(ord(SEPARATOR) + 1)}"
    return [File.relative_path >= prefix, File.relative_path < after]


def _tail(prefix: str) -> ColumnElement[str]:
    """Return the part of a path that follows this prefix.

    Returns:
        A string expression over ``File``.
    """
    return func.substr(File.relative_path, len(prefix) + 1)


def _narrowing(scope: FileFilter) -> list[ColumnElement[bool]]:
    """Return the clauses every listing narrowed by this filter shares.

    Returns:
        One boolean clause over ``File`` per axis the filter narrows.
    """
    clauses: list[ColumnElement[bool]] = []
    if scope.root_id is not None:
        clauses.append(File.root_id == scope.root_id)
    if scope.mark_id is not None:
        clauses.append(_carrying(scope.mark_id))
    if scope.stack_id is not None:
        clauses.append(_sitting_in(scope.stack_id))
    return clauses + _beneath(_prefix(scope.directory))


class FileRepository(FileRepositoryProtocol):
    """Reads and writes files in the index.

    Writes are flushed, never committed: the transaction boundary belongs to
    the service that opened it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(
        self,
        scope: FileFilter | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[FileDTO]:
        """Return indexed files, narrowed by the filter when one is given.

        Root and relative path are unique together, so the order is total and
        a page taken from it holds the same files however often it is read.

        Returns:
            The matching files, ordered by root and then relative path.
        """
        narrowed = scope or FileFilter()
        statement = (
            select(File)
            .where(*_narrowing(narrowed))
            .order_by(File.root_id, File.relative_path)
        )
        if narrowed.directory is not None:
            # Its own files and no deeper: what follows the directory is a
            # name, not a path.
            statement = statement.where(
                func.instr(_tail(_prefix(narrowed.directory)), SEPARATOR) == 0
            )
        if limit is not None:
            statement = statement.limit(limit).offset(offset)
        return [
            FileDTO.model_validate(record)
            for record in self._session.scalars(statement).all()
        ]

    def list_directories(self, scope: FileFilter) -> list[DirectorySummary]:
        """Return the directories sitting directly in the filter's directory.

        One row per first segment of what follows the directory, so a path
        naming several levels is counted under the one level up from here.

        Returns:
            The directories, ordered by name, each counted over everything
            beneath it that the rest of the filter keeps.
        """
        tail = _tail(_prefix(scope.directory))
        cut = func.instr(tail, SEPARATOR)
        name = func.substr(tail, 1, cut - 1)
        statement = (
            select(name.label("name"), count(File.id).label("files"))
            .where(*_narrowing(scope), cut > 0)
            .group_by(name)
            .order_by(name)
        )
        return [
            DirectorySummary(name=row.name, file_count=row.files)
            for row in self._session.execute(statement)
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
        """Insert or update files by root and relative path, a batch at a time.

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
        statement = upsert.on_conflict_do_update(
            index_elements=[File.root_id, File.relative_path],
            set_={"size": upsert.excluded.size, "mtime": upsert.excluded.mtime},
        )
        for batch in batched(wanted, BATCH, strict=False):
            self._session.execute(statement, list(batch))
        self._session.flush()
        return [FileDTO.model_validate(record) for record in self._read(wanted)]

    def _read(self, wanted: list[_FileRow]) -> list[File]:
        """Return the written files in the order they were given.

        Returns:
            One record per wanted root and relative path.
        """
        keys = [(file["root_id"], file["relative_path"]) for file in wanted]
        written: dict[tuple[int, str], File] = {}
        for batch in batched(keys, BATCH, strict=False):
            # populate_existing: the upsert went round the session, so a record
            # it changed is still in the identity map holding the size it had
            # before.
            records = self._session.scalars(
                select(File)
                .where(tuple_(File.root_id, File.relative_path).in_(batch))
                .execution_options(populate_existing=True)
            ).all()
            written.update(
                ((record.root_id, record.relative_path), record) for record in records
            )
        return [written[key] for key in keys]

    def delete_many(self, file_ids: Iterable[int]) -> None:
        """Delete the files with these ids, a batch at a time."""
        for batch in batched(file_ids, BATCH, strict=False):
            self._session.execute(delete(File).where(File.id.in_(batch)))
        self._session.flush()
        # The database cascaded the file_marks rows away without telling the
        # session, so anything it still holds from before is out of date.
        self._session.expire_all()
