"""Shared container and app fixtures for the TUI integration tests."""

from __future__ import annotations

import pytest

from acervus.inits.repositories import Repositories
from acervus.inits.services import Services
from acervus.inits.wiring import build_app

DOCS = "docs"
INBOX = "inbox.md"
NOTES = "notes.md"
CONTENT = "hello"


@pytest.fixture(name="repositories")
def repositories_fixture(tmp_path):
    return Repositories(tmp_path / "acervus.db")


@pytest.fixture(name="services")
def services_fixture(repositories):
    return Services(repositories)


# Built the way main() builds it, so the tests exercise the real assembly.
@pytest.fixture(name="app")
def app_fixture(services):
    return build_app(services)


# A root holding two files: inbox.md sorts before notes.md, so it is the first row.
@pytest.fixture(name="tree")
def tree_fixture(tmp_path):
    tree = tmp_path / "docs"
    tree.mkdir()
    for name in (INBOX, NOTES):
        (tree / name).write_text(CONTENT)
    return tree


@pytest.fixture(name="indexed")
def indexed_fixture(services, tree):
    services.roots.sync({DOCS: tree})
    services.scan.scan(DOCS)
    return services
