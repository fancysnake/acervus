"""Tests for config loading in inits."""

from pathlib import Path

from acervus.inits.config import load_config

SAMPLE_TOML = """\
[acervus]
db_path = "/tmp/acervus.db"

[acervus.roots]
docs = "/home/user/docs"
photos = "/home/user/photos"
"""

HOME_TOML = """\
[acervus]
db_path = "~/.local/share/acervus/acervus.db"

[acervus.roots]
docs = "~/docs"
"""

SAMPLE_DB_PATH = Path("/tmp/acervus.db")


class TestLoadConfig:
    @staticmethod
    def test_loads_from_toml(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(SAMPLE_TOML)

        config = load_config(config_path)

        assert config is not None
        assert config.db_path == SAMPLE_DB_PATH
        assert config.roots == {
            "docs": Path("/home/user/docs"),
            "photos": Path("/home/user/photos"),
        }

    @staticmethod
    def test_missing_file_returns_none(tmp_path):
        missing = tmp_path / "nonexistent.toml"

        assert load_config(missing) is None

    @staticmethod
    def test_home_relative_paths_are_expanded(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(HOME_TOML)

        config = load_config(config_path)

        assert config is not None
        assert config.db_path == Path.home() / ".local/share/acervus/acervus.db"
        assert config.roots == {"docs": Path.home() / "docs"}
