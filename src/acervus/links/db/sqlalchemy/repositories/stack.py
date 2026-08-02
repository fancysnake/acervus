"""The stack repository, backing the pacts protocol with SQLAlchemy."""

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.sql.functions import count

from acervus.links.db.sqlalchemy.models import File, Stack
from acervus.pacts.stack import (
    StackDTO,
    StackNotFoundError,
    StackRepositoryProtocol,
    StackSummary,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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

    def set_for_file(self, file_id: int, *, stack_id: int | None) -> None:
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
