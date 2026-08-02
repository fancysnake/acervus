"""Business operations on stacks."""

from typing import TYPE_CHECKING

from acervus.pacts.stack import StackNotFoundError, StackServiceProtocol
from acervus.specs.stack import clean_stack_name

if TYPE_CHECKING:
    from acervus.pacts.stack import StackDTO, StackRepositoryProtocol, StackSummary
    from acervus.pacts.transaction import TransactionProtocol


class StackService(StackServiceProtocol):
    """Moves files between stacks, one stack at a time."""

    def __init__(
        self, *, stacks: StackRepositoryProtocol, transaction: TransactionProtocol
    ) -> None:
        self._stacks = stacks
        self._transaction = transaction

    def list_all(self) -> list[StackSummary]:
        """Return every stack with its file count.

        Returns:
            Every stack, ordered by name.
        """
        return self._stacks.list_all()

    def for_file(self, file_id: int) -> StackDTO | None:
        """Return the stack this file sits in.

        Returns:
            The file's stack, or ``None`` if it sits in none.
        """
        return self._stacks.read_for_file(file_id)

    def add(self, file_id: int, *, name: str) -> StackDTO:
        """Move this file into the stack of this name.

        A file sits in at most one stack, so this moves rather than copies: the
        stack the file was in loses it, and is deleted if that leaves it empty.

        Returns:
            The stack the file now sits in.
        """
        cleaned = clean_stack_name(name)
        with self._transaction.atomic():
            try:
                stack = self._stacks.read_by_name(cleaned)
            except StackNotFoundError:
                stack = self._stacks.create(cleaned)
            self._drop_empty(self._leave(file_id, joining=stack.id))
            self._stacks.set_for_file(file_id, stack_id=stack.id)
            return stack

    def remove(self, file_id: int) -> None:
        """Take this file out of whatever stack it sits in.

        A stack left empty is deleted, so the stack list stays a list of stacks
        holding something.
        """
        with self._transaction.atomic():
            if (previous := self._stacks.read_for_file(file_id)) is None:
                return
            self._stacks.set_for_file(file_id, stack_id=None)
            self._drop_empty(previous.id)

    def _leave(self, file_id: int, *, joining: int) -> int | None:
        previous = self._stacks.read_for_file(file_id)
        if previous is None or previous.id == joining:
            return None
        self._stacks.set_for_file(file_id, stack_id=None)
        return previous.id

    def _drop_empty(self, stack_id: int | None) -> None:
        if stack_id is not None and self._stacks.count_files(stack_id) == 0:
            self._stacks.delete(stack_id)
