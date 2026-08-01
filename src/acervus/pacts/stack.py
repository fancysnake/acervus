"""Boundary contracts for the stack noun."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypedDict

from pydantic import BaseModel, ConfigDict


class StackNotFoundError(Exception):
    """No stack matches the requested identifier."""


class InvalidStackNameError(ValueError):
    """The proposed stack name breaks an invariant."""


class StackDTO(BaseModel):
    """A group a file can belong to, as read from the index."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StackWrite(TypedDict):
    """The fields needed to create a stack."""

    name: str


@dataclass(frozen=True, slots=True)
class StackSummary:
    """A stack alongside how many files sit in it."""

    id: int
    name: str
    file_count: int


class StackRepositoryProtocol(Protocol):
    """Data access for stacks and the files sitting in them."""

    def list_all(self) -> list[StackSummary]:
        """Return every stack with its file count, ordered by name."""

    def read_by_name(self, name: str) -> StackDTO:
        """Return the stack with this name, or raise ``StackNotFoundError``."""

    def read_for_file(self, file_id: int) -> StackDTO | None:
        """Return the stack this file sits in, or ``None`` if it sits in none."""

    def create(self, name: str) -> StackDTO:
        """Create a stack with this name and return it."""

    def set_for_file(self, file_id: int, *, stack_id: int | None) -> None:
        """Put this file in this stack, or take it out of any stack at ``None``."""

    def count_files(self, stack_id: int) -> int:
        """Return how many files sit in this stack."""

    def delete(self, stack_id: int) -> None:
        """Delete this stack, turning its files loose first."""


class StackServiceProtocol(Protocol):
    """Business operations on stacks."""

    def list_all(self) -> list[StackSummary]:
        """Return every stack with its file count."""

    def for_file(self, file_id: int) -> StackDTO | None:
        """Return the stack this file sits in, if it sits in one."""

    def add(self, file_id: int, *, name: str) -> StackDTO:
        """Move this file into the stack of this name, creating it if it is new."""

    def remove(self, file_id: int) -> None:
        """Take this file out of whatever stack it sits in."""
