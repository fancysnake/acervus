"""Tests for the stack repository in links, against a real database."""

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy import StackRepository
from acervus.pacts.stack import StackDTO, StackNotFoundError, StackSummary

UNKNOWN_ID = 404
TRIP = "iceland trip"
TAXES = "taxes 2026"


class TestStackRepository:
    @staticmethod
    def test_create_returns_a_dto_with_an_id(*, stacks):
        stack = stacks.create(TRIP)

        assert isinstance(stack, StackDTO)
        assert stack.name == TRIP
        assert stack.id

    @staticmethod
    def test_read_by_name(*, stacks):
        created = stacks.create(TRIP)

        assert stacks.read_by_name(TRIP).id == created.id

    @staticmethod
    def test_read_by_name_missing_raises(*, stacks):
        with pytest.raises(StackNotFoundError):
            stacks.read_by_name(TAXES)

    @staticmethod
    def test_list_all_is_empty_before_any_write(*, stacks):
        assert stacks.list_all() == []

    @staticmethod
    def test_list_all_counts_an_empty_stack_as_zero(*, stacks):
        stacks.create(TRIP)

        assert stacks.list_all() == [StackSummary(id=1, name=TRIP, file_count=0)]

    @staticmethod
    def test_list_all_is_ordered_by_name(*, stacks):
        stacks.create(TRIP)
        stacks.create(TAXES)

        assert [stack.name for stack in stacks.list_all()] == [TRIP, TAXES]

    @staticmethod
    def test_a_file_starts_in_no_stack(*, marked_file, stacks):
        assert stacks.read_for_file(marked_file.id) is None

    @staticmethod
    def test_set_for_file_puts_it_in(*, marked_file, stacks):
        stack = stacks.create(TRIP)

        stacks.set_for_file(marked_file.id, stack_id=stack.id)

        assert stacks.read_for_file(marked_file.id) == stack
        assert stacks.count_files(stack.id) == 1

    @staticmethod
    def test_set_for_file_none_takes_it_out(*, marked_file, stacks):
        stack = stacks.create(TRIP)
        stacks.set_for_file(marked_file.id, stack_id=stack.id)

        stacks.set_for_file(marked_file.id, stack_id=None)

        assert stacks.read_for_file(marked_file.id) is None
        assert stacks.count_files(stack.id) == 0

    @staticmethod
    def test_a_file_sits_in_one_stack_at_a_time(*, two_files, stacks):
        first = two_files[0]
        trip, taxes = stacks.create(TRIP), stacks.create(TAXES)
        stacks.set_for_file(first.id, stack_id=trip.id)

        stacks.set_for_file(first.id, stack_id=taxes.id)

        assert stacks.read_for_file(first.id) == taxes
        assert stacks.count_files(trip.id) == 0

    @staticmethod
    def test_a_stack_can_hold_two_files(*, two_files, stacks):
        stack = stacks.create(TRIP)

        for file in two_files:
            stacks.set_for_file(file.id, stack_id=stack.id)

        assert stacks.count_files(stack.id) == 1 + 1  # both files sit in it
        assert stacks.list_all()[0].file_count == 1 + 1  # and the summary agrees

    @staticmethod
    def test_setting_the_stack_of_an_unknown_file_is_harmless(*, stacks):
        stack = stacks.create(TRIP)

        stacks.set_for_file(UNKNOWN_ID, stack_id=stack.id)

        assert stacks.count_files(stack.id) == 0

    @staticmethod
    def test_count_files_is_zero_for_an_unknown_stack(*, stacks):
        assert stacks.count_files(UNKNOWN_ID) == 0

    @staticmethod
    def test_delete_turns_its_files_loose(*, marked_file, stacks):
        stack = stacks.create(TRIP)
        stacks.set_for_file(marked_file.id, stack_id=stack.id)

        stacks.delete(stack.id)

        assert stacks.list_all() == []
        assert stacks.read_for_file(marked_file.id) is None

    @staticmethod
    def test_delete_leaves_the_files_themselves(*, marked_file, files, stacks):
        stack = stacks.create(TRIP)
        stacks.set_for_file(marked_file.id, stack_id=stack.id)

        stacks.delete(stack.id)

        assert [file.id for file in files.list_all()] == [marked_file.id]

    @staticmethod
    def test_deleting_an_unknown_stack_is_harmless(*, stacks):
        stacks.delete(UNKNOWN_ID)

        assert stacks.list_all() == []

    @staticmethod
    def test_stacks_reach_the_database_file(*, engine, session, marked_file, stacks):
        stack = stacks.create(TRIP)
        stacks.set_for_file(marked_file.id, stack_id=stack.id)
        session.commit()

        with Session(engine) as fresh:
            reopened = StackRepository(fresh).list_all()

        assert reopened == [StackSummary(id=stack.id, name=TRIP, file_count=1)]
