"""Shared database fixtures for the links integration tests."""

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy.engine import open_database


@pytest.fixture(name="engine")
def engine_fixture(tmp_path):
    engine = open_database(tmp_path / "acervus.db")
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session
