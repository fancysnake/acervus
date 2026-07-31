"""Tests for AcervusConfig in pacts."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from acervus.pacts.config import AcervusConfig


class TestAcervusConfig:
    @staticmethod
    def test_valid_config() -> None:
        config = AcervusConfig(
            db_path=Path("/tmp/acervus.db"), roots={"docs": Path("/home/user/docs")},
        )

        assert config.db_path == Path("/tmp/acervus.db")
        assert config.roots == {"docs": Path("/home/user/docs")}

    @staticmethod
    def test_multiple_roots() -> None:
        config = AcervusConfig(
            db_path=Path("/tmp/acervus.db"),
            roots={
                "docs": Path("/home/user/docs"),
                "photos": Path("/home/user/photos"),
            },
        )

        assert len(config.roots) == 1 + 1  # docs + photos

    @staticmethod
    def test_empty_roots() -> None:
        config = AcervusConfig(db_path=Path("/tmp/acervus.db"), roots={})

        assert config.roots == {}

    @staticmethod
    def test_missing_db_path_raises() -> None:
        with pytest.raises(ValidationError):
            AcervusConfig(roots={"docs": Path("/tmp")})  # type: ignore[call-arg]

    @staticmethod
    def test_missing_roots_raises() -> None:
        with pytest.raises(ValidationError):
            AcervusConfig(db_path=Path("/tmp/acervus.db"))  # type: ignore[call-arg]

    @staticmethod
    def test_from_attributes() -> None:
        config = AcervusConfig.model_validate(
            {"db_path": Path("/tmp/acervus.db"), "roots": {}},
        )

        assert config.db_path == Path("/tmp/acervus.db")
