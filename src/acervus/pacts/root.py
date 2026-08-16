"""Boundary contracts for the root noun."""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


class RootNotFoundError(Exception):
    """No root matches the requested identifier."""


class RootUnavailableError(Exception):
    """The root is indexed, but its directory is not there to be read."""


class RootDTO(BaseModel):
    """A named directory Acervus indexes, as read from the index."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alias: str
    path: Path


class RootWrite(TypedDict):
    """The fields needed to create or update a root."""

    alias: str
    path: Path


class RootRepositoryProtocol(Protocol):
    """Data access for roots."""

    def list_all(self) -> list[RootDTO]:
        """Return every root in the index, ordered by alias."""

    def read_by_alias(self, alias: str) -> RootDTO:
        """Return the root with this alias, or raise ``RootNotFoundError``."""

    def upsert_many(self, roots: Iterable[RootWrite]) -> list[RootDTO]:
        """Insert or update roots by alias and return them."""

    def delete_many(self, aliases: Iterable[str]) -> None:
        """Delete the roots with these aliases, along with their files."""


class RootServiceProtocol(Protocol):
    """Business operations on roots."""

    def list_all(self) -> list[RootDTO]:
        """Return every indexed root."""

    def sync(self, configured: Mapping[str, Path]) -> list[RootDTO]:
        """Reconcile the index against the configured roots and return them."""
