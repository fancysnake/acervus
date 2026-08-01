"""Business operations on roots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from acervus.pacts.root import RootServiceProtocol, RootWrite

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from acervus.pacts.root import RootDTO, RootRepositoryProtocol
    from acervus.pacts.transaction import TransactionProtocol


class RootService(RootServiceProtocol):
    """Keeps the indexed roots in step with the configured ones."""

    def __init__(
        self, roots: RootRepositoryProtocol, transaction: TransactionProtocol
    ) -> None:
        self._roots = roots
        self._transaction = transaction

    def list_all(self) -> list[RootDTO]:
        """Return every indexed root.

        Returns:
            Every root, ordered by alias.
        """
        return self._roots.list_all()

    def sync(self, configured: Mapping[str, Path]) -> list[RootDTO]:
        """Reconcile the index against the configured roots.

        A root the config no longer names is dropped, taking its indexed files
        with it. A root the config names but the index lacks is inserted, and a
        root whose configured path has moved is updated. Roots the config and
        the index agree on are left untouched.

        Returns:
            Every root in the index once it matches the config.
        """
        with self._transaction.atomic():
            indexed = {root.alias: root for root in self._roots.list_all()}

            if dropped := [alias for alias in indexed if alias not in configured]:
                self._roots.delete_many(dropped)

            if written := [
                RootWrite(alias=alias, path=path)
                for alias, path in configured.items()
                if alias not in indexed or indexed[alias].path != path
            ]:
                self._roots.upsert_many(written)

            return self._roots.list_all()
