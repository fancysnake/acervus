"""Tests for config loading in inits."""

from __future__ import annotations

from pathlib import Path

import pytest

from acervus.inits.config import load_config

SAMPLE_TOML = """\
[acervus]
db_path = "/tmp/acervus.db"

[acervus.roots]
docs = "/home/user/docs"
photos = "/home/user/photos"
"""

SAMPLE_DB_PATH = Path("/tmp/acervus.db")


class TestLoadConfig:
    @staticmethod
    def test_loads_from_toml(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(SAMPLE_TOML)

        config = load_config(config_path)

        assert config.db_path == SAMPLE_DB_PATH
        assert config.roots == {
            "docs": Path("/home/user/docs"),
            "photos": Path("/home/user/photos"),
        }

    @staticmethod
    def test_missing_file_raises(tmp_path):
        missing = tmp_path / "nonexistent.toml"

        with pytest.raises(FileNotFoundError):
            load_config(missing)
