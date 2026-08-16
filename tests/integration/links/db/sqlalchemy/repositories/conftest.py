"""Shared repository fixtures for the links integration tests."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from acervus.links.db.sqlalchemy import (
    FileRepository,
    MarkRepository,
    RootRepository,
    StackRepository,
)

if TYPE_CHECKING:
    from acervus.pacts.file import FileWrite

DOCS = "docs"
DOCS_PATH = Path("/home/user/docs")
TODO = Path("notes/todo.md")
INBOX = Path("notes/inbox.md")
SIZE = 12
MTIME = 1.5


# Builds one file write, so the tests read as data rather than dict noise.
def a_file(root_id, relative_path, *, size=SIZE, mtime=MTIME) -> FileWrite:
    return {
        "root_id": root_id,
        "relative_path": relative_path,
        "size": size,
        "mtime": mtime,
    }


# The builder above, handed over as a fixture: a conftest shares functions the
# way it shares anything else.
@pytest.fixture(name="a_file")
def a_file_fixture():
    return a_file


@pytest.fixture(name="roots")
def roots_fixture(*, session):
    return RootRepository(session)


@pytest.fixture(name="files")
def files_fixture(*, session):
    return FileRepository(session)


@pytest.fixture(name="marks")
def marks_fixture(*, session):
    return MarkRepository(session)


@pytest.fixture(name="stacks")
def stacks_fixture(*, session):
    return StackRepository(session)


@pytest.fixture(name="marked_file")
def marked_file_fixture(*, roots, files):
    root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
    return files.upsert_many([a_file(root.id, TODO)])[0]


@pytest.fixture(name="two_files")
def two_files_fixture(*, roots, files):
    root = roots.upsert_many([{"alias": DOCS, "path": DOCS_PATH}])[0]
    return files.upsert_many([a_file(root.id, TODO), a_file(root.id, INBOX)])
