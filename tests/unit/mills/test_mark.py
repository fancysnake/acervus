"""Tests for the mark service in mills."""

# Pytest supplies fixtures by name, so a test taking three of them is not the
# argument-order hazard the positional limit guards against.
# pylint: disable=too-many-positional-arguments

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from acervus.mills.mark import MarkService
from acervus.pacts.mark import (
    InvalidMarkNameError,
    MarkDTO,
    MarkNotFoundError,
    MarkRepositoryProtocol,
    MarkSummary,
)
from acervus.pacts.transaction import TransactionProtocol

FILE_ID = 5
INVOICE = "invoice"
HOLIDAY = "holiday"
INVOICE_MARK = MarkDTO(id=1, name=INVOICE)
HOLIDAY_MARK = MarkDTO(id=2, name=HOLIDAY)
INVOICE_SUMMARY = MarkSummary(id=1, name=INVOICE, file_count=3)


@pytest.fixture(name="marks")
def marks_fixture():
    repository = Mock(spec=MarkRepositoryProtocol)
    repository.read_by_name.return_value = INVOICE_MARK
    repository.count_files.return_value = 1
    return repository


@pytest.fixture(name="transaction")
def transaction_fixture():
    return MagicMock(spec=TransactionProtocol)


@pytest.fixture(name="service")
def service_fixture(marks, transaction):
    return MarkService(marks=marks, transaction=transaction)


class TestListing:
    @staticmethod
    def test_list_all_delegates(service, marks, transaction):
        marks.list_all.return_value = [INVOICE_SUMMARY]

        assert service.list_all() == [INVOICE_SUMMARY]

        marks.list_all.assert_called_once_with()
        transaction.atomic.assert_not_called()

    @staticmethod
    def test_list_for_file_delegates(service, marks, transaction):
        marks.list_for_file.return_value = [INVOICE_MARK, HOLIDAY_MARK]

        assert service.list_for_file(FILE_ID) == [INVOICE_MARK, HOLIDAY_MARK]

        marks.list_for_file.assert_called_once_with(FILE_ID)
        transaction.atomic.assert_not_called()


class TestAdd:
    @staticmethod
    def test_it_attaches_an_existing_mark(service, marks):
        assert service.add(FILE_ID, name=INVOICE) == INVOICE_MARK

        marks.read_by_name.assert_called_once_with(INVOICE)
        marks.create.assert_not_called()
        marks.attach.assert_called_once_with(FILE_ID, mark_id=INVOICE_MARK.id)

    @staticmethod
    def test_it_creates_a_mark_the_index_lacks(service, marks):
        marks.read_by_name.side_effect = MarkNotFoundError(INVOICE)
        marks.create.return_value = INVOICE_MARK

        assert service.add(FILE_ID, name=INVOICE) == INVOICE_MARK

        marks.create.assert_called_once_with(INVOICE)
        marks.attach.assert_called_once_with(FILE_ID, mark_id=INVOICE_MARK.id)

    @staticmethod
    def test_it_cleans_the_name_first(service, marks):
        service.add(FILE_ID, name=f"  {INVOICE}  ")

        marks.read_by_name.assert_called_once_with(INVOICE)

    @staticmethod
    def test_a_bad_name_never_reaches_the_repository(service, marks, transaction):
        with pytest.raises(InvalidMarkNameError):
            service.add(FILE_ID, name="two words")

        marks.read_by_name.assert_not_called()
        marks.attach.assert_not_called()
        transaction.atomic.assert_not_called()

    @staticmethod
    def test_it_writes_inside_one_transaction(service, transaction):
        service.add(FILE_ID, name=INVOICE)

        transaction.atomic.assert_called_once_with()
        transaction.atomic.return_value.__enter__.assert_called_once_with()
        transaction.atomic.return_value.__exit__.assert_called_once()


class TestRemove:
    @staticmethod
    def test_it_detaches_the_mark(service, marks):
        service.remove(FILE_ID, name=INVOICE)

        marks.read_by_name.assert_called_once_with(INVOICE)
        marks.detach.assert_called_once_with(FILE_ID, mark_id=INVOICE_MARK.id)

    @staticmethod
    def test_a_mark_still_in_use_survives(service, marks):
        marks.count_files.return_value = 2

        service.remove(FILE_ID, name=INVOICE)

        marks.delete.assert_not_called()

    @staticmethod
    def test_a_mark_nothing_carries_is_deleted(service, marks):
        marks.count_files.return_value = 0

        service.remove(FILE_ID, name=INVOICE)

        marks.count_files.assert_called_once_with(INVOICE_MARK.id)
        marks.delete.assert_called_once_with(INVOICE_MARK.id)

    @staticmethod
    def test_an_unknown_mark_raises(service, marks):
        marks.read_by_name.side_effect = MarkNotFoundError(HOLIDAY)

        with pytest.raises(MarkNotFoundError):
            service.remove(FILE_ID, name=HOLIDAY)

        marks.detach.assert_not_called()

    @staticmethod
    def test_a_bad_name_never_reaches_the_repository(service, marks, transaction):
        with pytest.raises(InvalidMarkNameError):
            service.remove(FILE_ID, name="")

        marks.read_by_name.assert_not_called()
        transaction.atomic.assert_not_called()

    @staticmethod
    def test_it_writes_inside_one_transaction(service, transaction):
        service.remove(FILE_ID, name=INVOICE)

        transaction.atomic.assert_called_once_with()
        transaction.atomic.return_value.__enter__.assert_called_once_with()
        transaction.atomic.return_value.__exit__.assert_called_once()
