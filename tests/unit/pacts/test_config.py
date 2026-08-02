"""Tests for AcervusConfig in pacts."""

from pathlib import Path

from acervus.pacts.config import AcervusConfig


class TestAcervusConfig:
    @staticmethod
    def test_valid_config() -> None:
        config = AcervusConfig(
            db_path=Path("/tmp/acervus.db"), roots={"docs": Path("/home/user/docs")}
        )

        assert config.db_path == Path("/tmp/acervus.db")
        assert config.roots == {"docs": Path("/home/user/docs")}
