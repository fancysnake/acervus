"""Shared database fixtures for the links integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from acervus.links.db.sqlalchemy.engine import create_engine_from_path, init_db


@pytest.fixture(name="engine")
def engine_fixture(tmp_path):
    engine = create_engine_from_path(tmp_path / "acervus.db")
    init_db(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session
