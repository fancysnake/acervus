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

        A file id nothing indexes comes back out of the repository as
        ``StackFileNotFoundError``. A stack created for it a moment earlier
        goes back with the transaction, so a name aimed at a file a scan has
        since deleted leaves nothing behind.

        Returns:
            The stack the file now sits in.
        """
        cleaned = clean_stack_name(name)
        with self._transaction.atomic():
            try:
                stack = self._stacks.read_by_name(cleaned)
            except StackNotFoundError:
                stack = self._stacks.create(cleaned)
            self._move(file_id, stack_id=stack.id)
            return stack

    def remove(self, file_id: int) -> None:
        """Take this file out of whatever stack it sits in.

        A stack left empty is deleted, so the stack list stays a list of stacks
        holding something.
        """
        with self._transaction.atomic():
            self._move(file_id, stack_id=None)

    def _move(self, file_id: int, *, stack_id: int | None) -> None:
        """Point this file at this stack, and drop the one it emptied.

        Both directions are the same movement, so it is written once. Pointing
        the file at its new stack is what takes it out of the old one, which is
        why the count that decides whether the old one survives is read after.
        """
        previous = self._stacks.read_for_file(file_id)
        if (standing := None if previous is None else previous.id) == stack_id:
            return
        self._stacks.set_for_file(file_id, stack_id=stack_id)
        if standing is not None:
            self._drop_empty(standing)

    def _drop_empty(self, stack_id: int) -> None:
        if self._stacks.count_files(stack_id) == 0:
            self._stacks.delete(stack_id)
