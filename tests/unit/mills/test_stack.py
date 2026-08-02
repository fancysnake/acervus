"""Tests for the stack service in mills."""

# Pytest supplies fixtures by name, so a test taking three of them is not the
# argument-order hazard the positional limit guards against.
# pylint: disable=too-many-positional-arguments


from unittest.mock import MagicMock, Mock

import pytest

from acervus.mills.stack import StackService
from acervus.pacts.stack import (
    InvalidStackNameError,
    StackDTO,
    StackNotFoundError,
    StackRepositoryProtocol,
    StackSummary,
)
from acervus.pacts.transaction import TransactionProtocol

FILE_ID = 5
TRIP = "iceland trip"
TAXES = "taxes 2026"
TRIP_STACK = StackDTO(id=1, name=TRIP)
TAXES_STACK = StackDTO(id=2, name=TAXES)
TRIP_SUMMARY = StackSummary(id=1, name=TRIP, file_count=4)


@pytest.fixture(name="stacks")
def stacks_fixture():
    repository = Mock(spec=StackRepositoryProtocol)
    repository.read_by_name.return_value = TRIP_STACK
    repository.read_for_file.return_value = None
    repository.count_files.return_value = 1
    return repository


@pytest.fixture(name="transaction")
def transaction_fixture():
    return MagicMock(spec=TransactionProtocol)


@pytest.fixture(name="service")
def service_fixture(stacks, transaction):
    return StackService(stacks=stacks, transaction=transaction)


class TestListing:
    @staticmethod
    def test_list_all_delegates(service, stacks, transaction):
        stacks.list_all.return_value = [TRIP_SUMMARY]

        assert service.list_all() == [TRIP_SUMMARY]

        stacks.list_all.assert_called_once_with()
        transaction.atomic.assert_not_called()

    @staticmethod
    def test_for_file_delegates(service, stacks):
        stacks.read_for_file.return_value = TRIP_STACK

        assert service.for_file(FILE_ID) == TRIP_STACK

        stacks.read_for_file.assert_called_once_with(FILE_ID)

    @staticmethod
    def test_for_file_is_none_when_the_file_sits_loose(service):
        assert service.for_file(FILE_ID) is None


class TestAdd:
    @staticmethod
    def test_it_puts_the_file_in_an_existing_stack(service, stacks):
        assert service.add(FILE_ID, name=TRIP) == TRIP_STACK

        stacks.read_by_name.assert_called_once_with(TRIP)
        stacks.create.assert_not_called()
        stacks.set_for_file.assert_called_once_with(FILE_ID, stack_id=TRIP_STACK.id)

    @staticmethod
    def test_it_creates_a_stack_the_index_lacks(service, stacks):
        stacks.read_by_name.side_effect = StackNotFoundError(TRIP)
        stacks.create.return_value = TRIP_STACK

        assert service.add(FILE_ID, name=TRIP) == TRIP_STACK

        stacks.create.assert_called_once_with(TRIP)

    @staticmethod
    def test_it_cleans_the_name_first(service, stacks):
        service.add(FILE_ID, name="  iceland   trip ")

        stacks.read_by_name.assert_called_once_with(TRIP)

    @staticmethod
    def test_a_bad_name_never_reaches_the_repository(service, stacks, transaction):
        with pytest.raises(InvalidStackNameError):
            service.add(FILE_ID, name="   ")

        stacks.read_by_name.assert_not_called()
        transaction.atomic.assert_not_called()

    @staticmethod
    def test_it_writes_inside_one_transaction(service, transaction):
        service.add(FILE_ID, name=TRIP)

        transaction.atomic.assert_called_once_with()
        transaction.atomic.return_value.__enter__.assert_called_once_with()
        transaction.atomic.return_value.__exit__.assert_called_once()


class TestAddMoves:
    @staticmethod
    def test_a_file_leaves_the_stack_it_was_in(service, stacks):
        stacks.read_for_file.return_value = TAXES_STACK

        service.add(FILE_ID, name=TRIP)

        assert stacks.set_for_file.call_args_list[0].kwargs == {"stack_id": None}
        assert stacks.set_for_file.call_args_list[-1].kwargs == {
            "stack_id": TRIP_STACK.id
        }

    @staticmethod
    def test_the_stack_it_left_survives_if_others_remain(service, stacks):
        stacks.read_for_file.return_value = TAXES_STACK
        stacks.count_files.return_value = 3

        service.add(FILE_ID, name=TRIP)

        stacks.delete.assert_not_called()

    @staticmethod
    def test_the_stack_it_emptied_is_deleted(service, stacks):
        stacks.read_for_file.return_value = TAXES_STACK
        stacks.count_files.return_value = 0

        service.add(FILE_ID, name=TRIP)

        stacks.count_files.assert_called_once_with(TAXES_STACK.id)
        stacks.delete.assert_called_once_with(TAXES_STACK.id)

    @staticmethod
    def test_adding_to_the_stack_it_is_already_in_deletes_nothing(service, stacks):
        stacks.read_for_file.return_value = TRIP_STACK
        stacks.count_files.return_value = 0

        service.add(FILE_ID, name=TRIP)

        stacks.delete.assert_not_called()


class TestRemove:
    @staticmethod
    def test_it_takes_the_file_out(service, stacks):
        stacks.read_for_file.return_value = TRIP_STACK

        service.remove(FILE_ID)

        stacks.set_for_file.assert_called_once_with(FILE_ID, stack_id=None)

    @staticmethod
    def test_a_loose_file_is_left_alone(service, stacks):
        service.remove(FILE_ID)

        stacks.set_for_file.assert_not_called()
        stacks.delete.assert_not_called()

    @staticmethod
    def test_a_stack_still_holding_files_survives(service, stacks):
        stacks.read_for_file.return_value = TRIP_STACK
        stacks.count_files.return_value = 2

        service.remove(FILE_ID)

        stacks.delete.assert_not_called()

    @staticmethod
    def test_a_stack_left_empty_is_deleted(service, stacks):
        stacks.read_for_file.return_value = TRIP_STACK
        stacks.count_files.return_value = 0

        service.remove(FILE_ID)

        stacks.delete.assert_called_once_with(TRIP_STACK.id)

    @staticmethod
    def test_it_writes_inside_one_transaction(service, stacks, transaction):
        stacks.read_for_file.return_value = TRIP_STACK

        service.remove(FILE_ID)

        transaction.atomic.assert_called_once_with()
        transaction.atomic.return_value.__exit__.assert_called_once()
