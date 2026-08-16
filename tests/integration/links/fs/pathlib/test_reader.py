"""Tests for the pathlib filesystem reader in links, against a real directory."""

import os
from pathlib import Path

import pytest

from acervus.links.fs.pathlib.reader import PathlibFilesystemReader
from acervus.pacts.filesystem import RootLostError

TODO = Path("notes/todo.md")
INBOX = Path("inbox.md")
DEEP = Path("a/b/c/deep.txt")
CONTENT = "hello"
VENV = ".venv"
BURIED = Path(".venv/lib/site-packages/thing.py")
NESTED_VENV = Path("project/.venv/pyvenv.cfg")
CACHED = Path("notes/todo.pyc")
SHUT = Path("shut")
SHUT_AWAY = Path("shut/away.md")
NO_ACCESS = 0o000
OWNER_ONLY = 0o700

# A directory closed with chmod stays open to root, so the one test that needs
# an unreadable directory cannot say anything when the suite runs as root.
as_root = pytest.mark.skipif(os.geteuid() == 0, reason="root reads a closed directory")


@pytest.fixture(name="reader")
def reader_fixture():
    return PathlibFilesystemReader()


def write(root: Path, relative_path: Path, *, content: str = CONTENT) -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


class TestPathlibFilesystemReader:
    @staticmethod
    def test_it_yields_every_file(*, reader, tmp_path):
        write(tmp_path, TODO)
        write(tmp_path, INBOX)

        found = {info.relative_path for info in reader.walk(tmp_path).files}

        assert found == {TODO, INBOX}

    @staticmethod
    def test_it_descends_into_nested_directories(*, reader, tmp_path):
        write(tmp_path, DEEP)

        found = [info.relative_path for info in reader.walk(tmp_path).files]

        assert found == [DEEP]

    @staticmethod
    def test_it_reports_size_and_mtime(*, reader, tmp_path):
        target = write(tmp_path, INBOX)

        info = reader.walk(tmp_path).files[0]

        assert info.size == len(CONTENT)
        assert info.mtime == pytest.approx(target.stat().st_mtime)

    @staticmethod
    def test_it_skips_directories_themselves(*, reader, tmp_path):
        write(tmp_path, DEEP)
        (tmp_path / "empty").mkdir()

        found = [info.relative_path for info in reader.walk(tmp_path).files]

        assert found == [DEEP]

    @staticmethod
    def test_an_empty_root_reads_as_empty(*, reader, tmp_path):
        walked = reader.walk(tmp_path)

        assert not walked.files
        assert not walked.unread

    @staticmethod
    def test_a_missing_root_is_lost_rather_than_empty(*, reader, tmp_path):
        with pytest.raises(RootLostError):
            reader.walk(tmp_path / "gone")

    @staticmethod
    def test_a_directory_that_is_there_exists(*, reader, tmp_path):
        assert reader.exists(tmp_path)

    @staticmethod
    def test_a_directory_that_is_not_there_does_not(*, reader, tmp_path):
        assert not reader.exists(tmp_path / "gone")

    @staticmethod
    def test_a_file_is_not_a_root(*, reader, tmp_path):
        assert not reader.exists(write(tmp_path, INBOX))

    @staticmethod
    def test_paths_are_relative_to_the_root(*, reader, tmp_path):
        write(tmp_path, TODO)

        info = reader.walk(tmp_path).files[0]

        assert not info.relative_path.is_absolute()
        assert tmp_path / info.relative_path == tmp_path / TODO

    @staticmethod
    def test_a_broken_symlink_is_skipped(*, reader, tmp_path):
        (tmp_path / "dangling").symlink_to(tmp_path / "gone")

        assert not reader.walk(tmp_path).files

    @staticmethod
    def test_nothing_is_ignored_unless_a_pattern_says_so(*, reader, tmp_path):
        write(tmp_path, BURIED)

        found = [info.relative_path for info in reader.walk(tmp_path).files]

        assert found == [BURIED]


class TestADirectoryThatCannotBeRead:
    """A subtree nothing could look at is named rather than reported as empty."""

    @staticmethod
    @as_root
    def test_it_is_named_in_unread(*, reader, tmp_path):
        write(tmp_path, SHUT_AWAY)
        closed = tmp_path / SHUT
        closed.chmod(NO_ACCESS)
        try:
            walked = reader.walk(tmp_path)
        finally:
            closed.chmod(OWNER_ONLY)

        assert walked.unread == (SHUT,)

    @staticmethod
    @as_root
    def test_its_files_are_not_reported(*, reader, tmp_path):
        write(tmp_path, SHUT_AWAY)
        closed = tmp_path / SHUT
        closed.chmod(NO_ACCESS)
        try:
            walked = reader.walk(tmp_path)
        finally:
            closed.chmod(OWNER_ONLY)

        assert not walked.files

    @staticmethod
    @as_root
    def test_the_rest_of_the_tree_is_walked_all_the_same(*, reader, tmp_path):
        write(tmp_path, SHUT_AWAY)
        write(tmp_path, INBOX)
        closed = tmp_path / SHUT
        closed.chmod(NO_ACCESS)
        try:
            walked = reader.walk(tmp_path)
        finally:
            closed.chmod(OWNER_ONLY)

        assert [info.relative_path for info in walked.files] == [INBOX]

    @staticmethod
    def test_a_tree_nothing_blocks_reports_nothing_unread(*, reader, tmp_path):
        write(tmp_path, DEEP)

        assert not reader.walk(tmp_path).unread


class TestIgnoringWhatTheIndexShouldNotHold:
    @staticmethod
    def test_a_named_directory_is_skipped_whole(*, tmp_path):
        write(tmp_path, BURIED)
        write(tmp_path, INBOX)

        found = [
            info.relative_path
            for info in PathlibFilesystemReader([VENV]).walk(tmp_path).files
        ]

        assert found == [INBOX]

    @staticmethod
    def test_a_pattern_names_a_directory_at_any_depth(*, tmp_path):
        write(tmp_path, NESTED_VENV)
        write(tmp_path, TODO)

        found = [
            info.relative_path
            for info in PathlibFilesystemReader([VENV]).walk(tmp_path).files
        ]

        assert found == [TODO]

    @staticmethod
    def test_a_glob_names_files_too(*, tmp_path):
        write(tmp_path, CACHED)
        write(tmp_path, TODO)

        found = [
            info.relative_path
            for info in PathlibFilesystemReader(["*.pyc"]).walk(tmp_path).files
        ]

        assert found == [TODO]

    @staticmethod
    def test_a_pattern_matching_nothing_leaves_the_tree_alone(*, tmp_path):
        write(tmp_path, INBOX)

        found = [
            info.relative_path
            for info in PathlibFilesystemReader(["nothing-here"]).walk(tmp_path).files
        ]

        assert found == [INBOX]

    @staticmethod
    def test_a_tree_that_is_only_ignored_reads_as_empty(*, tmp_path):
        write(tmp_path, BURIED)

        assert not PathlibFilesystemReader([VENV]).walk(tmp_path).files

    @staticmethod
    def test_an_ignored_directory_is_not_unread(*, tmp_path):
        write(tmp_path, BURIED)

        assert not PathlibFilesystemReader([VENV]).walk(tmp_path).unread
