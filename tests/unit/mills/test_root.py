"""Tests for the root service in mills."""

# Pytest supplies fixtures by name, so a test taking three of them is not the
# argument-order hazard the positional limit guards against.
# pylint: disable=too-many-positional-arguments


from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from acervus.mills.root import RootService
from acervus.pacts.root import RootDTO, RootRepositoryProtocol
from acervus.pacts.transaction import TransactionProtocol

DOCS = "docs"
PHOTOS = "photos"
MUSIC = "music"

DOCS_ROOT = RootDTO(id=1, alias=DOCS, path=Path("/home/user/docs"))
PHOTOS_ROOT = RootDTO(id=2, alias=PHOTOS, path=Path("/home/user/photos"))
MUSIC_ROOT = RootDTO(id=3, alias=MUSIC, path=Path("/home/user/music"))
MOVED_ROOT = RootDTO(id=1, alias=DOCS, path=Path("/mnt/archive/docs"))


@pytest.fixture(name="roots")
def roots_fixture():
    return Mock(spec=RootRepositoryProtocol)


@pytest.fixture(name="transaction")
def transaction_fixture():
    return MagicMock(spec=TransactionProtocol)


@pytest.fixture(name="service")
def service_fixture(roots, transaction):
    return RootService(roots=roots, transaction=transaction)


class TestListAll:
    @staticmethod
    def test_delegates_to_the_repository(service, roots, transaction):
        roots.list_all.return_value = [DOCS_ROOT]

        assert service.list_all() == [DOCS_ROOT]

        roots.list_all.assert_called_once_with()
        transaction.atomic.assert_not_called()


class TestSync:
    @staticmethod
    def test_inserts_a_root_new_to_the_config(service, roots):
        roots.list_all.side_effect = [[], [DOCS_ROOT]]

        assert service.sync({DOCS: DOCS_ROOT.path}) == [DOCS_ROOT]

        roots.upsert_many.assert_called_once_with(
            [{"alias": DOCS, "path": DOCS_ROOT.path}]
        )
        roots.delete_many.assert_not_called()

    @staticmethod
    def test_updates_a_root_whose_path_changed(service, roots):
        roots.list_all.side_effect = [[DOCS_ROOT], [MOVED_ROOT]]

        assert service.sync({DOCS: MOVED_ROOT.path}) == [MOVED_ROOT]

        roots.upsert_many.assert_called_once_with(
            [{"alias": DOCS, "path": MOVED_ROOT.path}]
        )
        roots.delete_many.assert_not_called()

    @staticmethod
    def test_drops_a_root_no_longer_configured(service, roots):
        roots.list_all.side_effect = [[DOCS_ROOT, PHOTOS_ROOT], [DOCS_ROOT]]

        assert service.sync({DOCS: DOCS_ROOT.path}) == [DOCS_ROOT]

        roots.delete_many.assert_called_once_with([PHOTOS])
        roots.upsert_many.assert_not_called()

    @staticmethod
    def test_leaves_an_unchanged_root_alone(service, roots):
        roots.list_all.side_effect = [[DOCS_ROOT], [DOCS_ROOT]]

        assert service.sync({DOCS: DOCS_ROOT.path}) == [DOCS_ROOT]

        roots.upsert_many.assert_not_called()
        roots.delete_many.assert_not_called()

    @staticmethod
    def test_an_empty_config_drops_every_root(service, roots):
        roots.list_all.side_effect = [[DOCS_ROOT, PHOTOS_ROOT], []]

        assert service.sync({}) == []

        roots.delete_many.assert_called_once_with([DOCS, PHOTOS])
        roots.upsert_many.assert_not_called()

    @staticmethod
    def test_inserts_drops_and_updates_together(service, roots):
        roots.list_all.side_effect = [
            [DOCS_ROOT, PHOTOS_ROOT],
            [MOVED_ROOT, MUSIC_ROOT],
        ]

        synced = service.sync({DOCS: MOVED_ROOT.path, MUSIC: MUSIC_ROOT.path})

        assert synced == [MOVED_ROOT, MUSIC_ROOT]
        roots.delete_many.assert_called_once_with([PHOTOS])
        roots.upsert_many.assert_called_once_with(
            [
                {"alias": DOCS, "path": MOVED_ROOT.path},
                {"alias": MUSIC, "path": MUSIC_ROOT.path},
            ]
        )

    @staticmethod
    def test_reconciles_inside_one_transaction(service, roots, transaction):
        roots.list_all.side_effect = [[], [DOCS_ROOT]]

        service.sync({DOCS: DOCS_ROOT.path})

        transaction.atomic.assert_called_once_with()
        transaction.atomic.return_value.__enter__.assert_called_once_with()
        transaction.atomic.return_value.__exit__.assert_called_once()

    @staticmethod
    def test_a_failing_write_propagates_so_the_transaction_rolls_back(service, roots):
        roots.list_all.side_effect = [[], [DOCS_ROOT]]
        roots.upsert_many.side_effect = RuntimeError("the database went away")

        with pytest.raises(RuntimeError):
            service.sync({DOCS: DOCS_ROOT.path})
