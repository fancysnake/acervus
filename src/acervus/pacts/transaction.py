"""Boundary contract for the transaction port."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractContextManager


class TransactionProtocol(Protocol):
    """A transaction boundary a service opens around a multi-repository write."""

    def atomic(self) -> AbstractContextManager[None]:
        """Commit on clean exit, roll back on exception."""
