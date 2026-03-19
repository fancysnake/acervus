"""Database engine creation and initialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from acervus.links.db.models import Base

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine


def create_engine_from_path(db_path: Path) -> Engine:
    url = f"sqlite:///{db_path}"
    return create_engine(url)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
