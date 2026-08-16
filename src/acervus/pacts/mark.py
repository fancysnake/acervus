"""Boundary contracts for the mark noun."""

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class MarkNotFoundError(Exception):
    """No mark matches the requested identifier."""


class InvalidMarkNameError(ValueError):
    """The proposed mark name breaks an invariant."""


class MarkDTO(BaseModel):
    """A label a file can carry, as read from the index."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


@dataclass(frozen=True, slots=True)
class MarkSummary:
    """A mark alongside how many files carry it."""

    id: int
    name: str
    file_count: int


class MarkRepositoryProtocol(Protocol):
    """Data access for marks and the files carrying them."""

    def list_all(self) -> list[MarkSummary]:
        """Return every mark with its file count, ordered by name."""

    def list_for_file(self, file_id: int) -> list[MarkDTO]:
        """Return the marks this file carries, ordered by name."""

    def read_by_name(self, name: str) -> MarkDTO:
        """Return the mark with this name, or raise ``MarkNotFoundError``."""

    def create(self, name: str) -> MarkDTO:
        """Create a mark with this name and return it."""

    def attach(self, file_id: int, *, mark_id: int) -> None:
        """Put this mark on this file, doing nothing if it is already there."""

    def detach(self, file_id: int, *, mark_id: int) -> None:
        """Take this mark off this file, doing nothing if it is not there."""

    def count_files(self, mark_id: int) -> int:
        """Return how many files carry this mark."""

    def delete(self, mark_id: int) -> None:
        """Delete this mark, detaching it from every file first."""


class MarkServiceProtocol(Protocol):
    """Business operations on marks."""

    def list_all(self) -> list[MarkSummary]:
        """Return every mark with its file count."""

    def list_for_file(self, file_id: int) -> list[MarkDTO]:
        """Return the marks this file carries."""

    def add(self, file_id: int, *, name: str) -> MarkDTO:
        """Put a mark of this name on this file, creating it if it is new."""

    def remove(self, file_id: int, *, name: str) -> None:
        """Take this mark off this file, dropping the mark if nothing carries it."""
