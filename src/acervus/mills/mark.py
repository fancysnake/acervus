"""Business operations on marks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from acervus.pacts.mark import MarkNotFoundError, MarkServiceProtocol
from acervus.specs.mark import clean_mark_name

if TYPE_CHECKING:
    from acervus.pacts.mark import MarkDTO, MarkRepositoryProtocol, MarkSummary
    from acervus.pacts.transaction import TransactionProtocol


class MarkService(MarkServiceProtocol):
    """Puts marks on files and takes them off again."""

    def __init__(
        self, *, marks: MarkRepositoryProtocol, transaction: TransactionProtocol
    ) -> None:
        self._marks = marks
        self._transaction = transaction

    def list_all(self) -> list[MarkSummary]:
        """Return every mark with its file count.

        Returns:
            Every mark, ordered by name.
        """
        return self._marks.list_all()

    def list_for_file(self, file_id: int) -> list[MarkDTO]:
        """Return the marks this file carries.

        Returns:
            The file's marks, ordered by name.
        """
        return self._marks.list_for_file(file_id)

    def add(self, file_id: int, *, name: str) -> MarkDTO:
        """Put a mark of this name on this file.

        The mark is created the first time it is used, so marks come into
        being by being applied rather than by being declared.

        Returns:
            The mark now on the file.
        """
        cleaned = clean_mark_name(name)
        with self._transaction.atomic():
            try:
                mark = self._marks.read_by_name(cleaned)
            except MarkNotFoundError:
                mark = self._marks.create(cleaned)
            self._marks.attach(file_id, mark_id=mark.id)
            return mark

    def remove(self, file_id: int, *, name: str) -> None:
        """Take this mark off this file.

        A mark no file carries any more is deleted, so the mark list stays a
        list of marks in use rather than a graveyard of past ones.
        """
        cleaned = clean_mark_name(name)
        with self._transaction.atomic():
            mark = self._marks.read_by_name(cleaned)
            self._marks.detach(file_id, mark_id=mark.id)
            if self._marks.count_files(mark.id) == 0:
                self._marks.delete(mark.id)
