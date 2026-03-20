"""Tests for specs configuration model."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from acervus.pacts.config import AcervusConfig

SAMPLE_DB_PATH = Path("/home/user/.local/share/acervus/acervus.db")


class TestAcervusConfig:
    @staticmethod
    def test_valid_config():
        config = AcervusConfig(
            db_path=SAMPLE_DB_PATH, roots={"docs": Path("/home/user/docs")},
        )

        assert config.db_path == SAMPLE_DB_PATH
        assert config.roots == {"docs": Path("/home/user/docs")}

    @staticmethod
    def test_multiple_roots():
        roots = {"docs": Path("/home/user/docs"), "photos": Path("/home/user/photos")}
        config = AcervusConfig(db_path=SAMPLE_DB_PATH, roots=roots)

        assert len(config.roots) == 1 + 1  # docs + photos

    @staticmethod
    def test_empty_roots():
        config = AcervusConfig(db_path=SAMPLE_DB_PATH, roots={})

        assert config.roots == {}

    @staticmethod
    def test_missing_db_path():
        with pytest.raises(ValidationError):
            AcervusConfig(roots={})  # type: ignore[call-arg]

    @staticmethod
    def test_missing_roots():
        with pytest.raises(ValidationError):
            AcervusConfig(db_path=SAMPLE_DB_PATH)  # type: ignore[call-arg]
