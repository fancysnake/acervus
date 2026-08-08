"""Tests for the pathlib filesystem reader in links, against a real directory."""

from pathlib import Path

import pytest

from acervus.links.fs.pathlib import PathlibFilesystemReader

TODO = Path("notes/todo.md")
INBOX = Path("inbox.md")
DEEP = Path("a/b/c/deep.txt")
CONTENT = "hello"
VANISHING = ("a.md", "b.md", "c.md")


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

        found = {info.relative_path for info in reader.walk(tmp_path)}

        assert found == {TODO, INBOX}

    @staticmethod
    def test_it_descends_into_nested_directories(*, reader, tmp_path):
        write(tmp_path, DEEP)

        found = [info.relative_path for info in reader.walk(tmp_path)]

        assert found == [DEEP]

    @staticmethod
    def test_it_reports_size_and_mtime(*, reader, tmp_path):
        target = write(tmp_path, INBOX)

        info = next(iter(reader.walk(tmp_path)))

        assert info.size == len(CONTENT)
        assert info.mtime == pytest.approx(target.stat().st_mtime)

    @staticmethod
    def test_it_skips_directories_themselves(*, reader, tmp_path):
        write(tmp_path, DEEP)
        (tmp_path / "empty").mkdir()

        found = [info.relative_path for info in reader.walk(tmp_path)]

        assert found == [DEEP]

    @staticmethod
    def test_an_empty_root_yields_nothing(*, reader, tmp_path):
        assert not list(reader.walk(tmp_path))

    @staticmethod
    def test_a_missing_root_yields_nothing(*, reader, tmp_path):
        assert not list(reader.walk(tmp_path / "gone"))

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

        info = next(iter(reader.walk(tmp_path)))

        assert not info.relative_path.is_absolute()
        assert tmp_path / info.relative_path == tmp_path / TODO

    @staticmethod
    def test_a_broken_symlink_is_skipped(*, reader, tmp_path):
        (tmp_path / "dangling").symlink_to(tmp_path / "gone")

        assert not list(reader.walk(tmp_path))

    @staticmethod
    def test_a_file_that_vanishes_mid_walk_is_skipped(*, reader, tmp_path):
        for name in VANISHING:
            write(tmp_path, Path(name))
        walked = reader.walk(tmp_path)
        first = next(walked)

        for name in VANISHING:
            (tmp_path / name).unlink()

        assert first.relative_path in {Path(name) for name in VANISHING}
        assert not list(walked)

    @staticmethod
    def test_it_walks_lazily(*, reader, tmp_path):
        write(tmp_path, TODO)
        walked = reader.walk(tmp_path)

        write(tmp_path, INBOX)

        assert {info.relative_path for info in walked} == {TODO, INBOX}
