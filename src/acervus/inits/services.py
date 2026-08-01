"""The service container, flat: one property per service."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from acervus.mills.root import RootService

if TYPE_CHECKING:
    from acervus.inits.repositories import Repositories


class Services:
    """Builds each service over the repositories and transaction it asks for."""

    def __init__(self, repositories: Repositories) -> None:
        self._repositories = repositories

    @cached_property
    def roots(self) -> RootService:
        """Return the root service."""
        return RootService(self._repositories.roots, self._repositories.transaction)
