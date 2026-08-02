"""Tests for the pathlib filesystem reader in links, against a real directory."""

# Pytest supplies fixtures by name, so a test taking three of them is not the
# argument-order hazard the positional limit guards against.
# pylint: disable=too-many-positional-arguments


from pathlib import Path

import pytest

from acervus.links.fs.pathlib import PathlibFilesystemReader

TODO = Path("notes/todo.md")
INBOX = Path("inbox.md")
DEEP = Path("a/b/c/deep.txt")
CONTENT = "hello"


@pytest.fixture(name="reader")
def reader_fixture():
    return PathlibFilesystemReader()


def write(root: Path, relative_path: Path, content: str = CONTENT) -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


class TestPathlibFilesystemReader:
    @staticmethod
    def test_it_yields_every_file(reader, tmp_path):
        write(tmp_path, TODO)
        write(tmp_path, INBOX)

        found = {info.relative_path for info in reader.walk(tmp_path)}

        assert found == {TODO, INBOX}

    @staticmethod
    def test_it_descends_into_nested_directories(reader, tmp_path):
        write(tmp_path, DEEP)

        found = [info.relative_path for info in reader.walk(tmp_path)]

        assert found == [DEEP]

    @staticmethod
    def test_it_reports_size_and_mtime(reader, tmp_path):
        target = write(tmp_path, INBOX)

        info = next(iter(reader.walk(tmp_path)))

        assert info.size == len(CONTENT)
        assert info.mtime == pytest.approx(target.stat().st_mtime)

    @staticmethod
    def test_it_skips_directories_themselves(reader, tmp_path):
        write(tmp_path, DEEP)
        (tmp_path / "empty").mkdir()

        found = [info.relative_path for info in reader.walk(tmp_path)]

        assert found == [DEEP]

    @staticmethod
    def test_an_empty_root_yields_nothing(reader, tmp_path):
        assert not list(reader.walk(tmp_path))

    @staticmethod
    def test_a_missing_root_yields_nothing(reader, tmp_path):
        assert not list(reader.walk(tmp_path / "gone"))

    @staticmethod
    def test_paths_are_relative_to_the_root(reader, tmp_path):
        write(tmp_path, TODO)

        info = next(iter(reader.walk(tmp_path)))

        assert not info.relative_path.is_absolute()
        assert tmp_path / info.relative_path == tmp_path / TODO

    @staticmethod
    def test_it_walks_lazily(reader, tmp_path):
        write(tmp_path, TODO)
        walked = reader.walk(tmp_path)

        write(tmp_path, INBOX)

        assert {info.relative_path for info in walked} == {TODO, INBOX}
