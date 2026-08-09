"""Tests for config loading in inits."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from acervus.inits import config as config_module
from acervus.inits.config import load_config
from acervus.inits.wiring import BAD_CONFIG_MESSAGE, NO_CONFIG_MESSAGE, main
from acervus.pacts.config import DEFAULT_IGNORE

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

IGNORE_TOML = """\
[acervus]
db_path = "/tmp/acervus.db"
ignore = [".venv", "*.pyc"]

[acervus.roots]
docs = "/home/user/docs"
"""

WRONG_SECTION_TOML = """\
[acrevus]
db_path = "/tmp/acervus.db"
"""

NO_DB_PATH_TOML = """\
[acervus]

[acervus.roots]
docs = "/home/user/docs"
"""

SAMPLE_DB_PATH = Path("/tmp/acervus.db")
SECTION = "acervus"
DB_PATH_FIELD = "db_path"
NOWHERE = Path("/nonexistent/acervus/config.toml")


@pytest.fixture(name="_malformed_config")
def malformed_config_fixture(monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(WRONG_SECTION_TOML)
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", config_path)


@pytest.fixture(name="_no_config")
def no_config_fixture(monkeypatch):
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", NOWHERE)


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
    def test_it_reads_the_ignore_list(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(IGNORE_TOML)

        config = load_config(config_path)

        assert config is not None
        assert config.ignore == (".venv", "*.pyc")

    @staticmethod
    def test_a_file_that_says_nothing_keeps_the_default_ignore_list(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(SAMPLE_TOML)

        config = load_config(config_path)

        assert config is not None
        assert config.ignore == DEFAULT_IGNORE

    @staticmethod
    def test_missing_file_returns_none(tmp_path):
        missing = tmp_path / "nonexistent.toml"

        assert load_config(missing) is None

    @staticmethod
    def test_a_file_without_the_section_says_which_is_missing(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(WRONG_SECTION_TOML)

        with pytest.raises(ValidationError) as raised:
            load_config(config_path)

        assert SECTION in str(raised.value)

    @staticmethod
    def test_a_file_missing_a_field_says_which(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(NO_DB_PATH_TOML)

        with pytest.raises(ValidationError) as raised:
            load_config(config_path)

        assert DB_PATH_FIELD in str(raised.value)

    @staticmethod
    def test_home_relative_paths_are_expanded(tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(HOME_TOML)

        config = load_config(config_path)

        assert config is not None
        assert config.db_path == Path.home() / ".local/share/acervus/acervus.db"
        assert config.roots == {"docs": Path.home() / "docs"}


# A file that is missing and a file that is malformed are the same kind of
# mistake, so neither may reach the user as a traceback.
class TestStartingWithoutUsableConfig:
    @staticmethod
    @pytest.mark.usefixtures("_no_config")
    def test_a_missing_file_is_reported(capsys):
        with pytest.raises(SystemExit):
            main()

        assert NO_CONFIG_MESSAGE in capsys.readouterr().err

    @staticmethod
    @pytest.mark.usefixtures("_malformed_config")
    def test_a_malformed_file_is_reported_too(capsys):
        with pytest.raises(SystemExit):
            main()

        assert BAD_CONFIG_MESSAGE.splitlines()[0] in capsys.readouterr().err

    @staticmethod
    @pytest.mark.usefixtures("_malformed_config")
    def test_a_malformed_file_names_what_is_wrong(capsys):
        with pytest.raises(SystemExit):
            main()

        assert SECTION in capsys.readouterr().err
