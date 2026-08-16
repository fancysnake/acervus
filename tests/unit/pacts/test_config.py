"""Tests for AcervusConfig in pacts."""

from pathlib import Path

from acervus.pacts.config import DEFAULT_IGNORE, AcervusConfig

VENV = ".venv"


class TestAcervusConfig:
    @staticmethod
    def test_valid_config() -> None:
        config = AcervusConfig(
            db_path=Path("/tmp/acervus.db"), roots={"docs": Path("/home/user/docs")}
        )

        assert config.db_path == Path("/tmp/acervus.db")
        assert config.roots == {"docs": Path("/home/user/docs")}


class TestPathsAPersonWrote:
    @staticmethod
    def test_a_home_relative_database_is_expanded() -> None:
        config = AcervusConfig(db_path=Path("~/acervus.db"), roots={})

        assert config.db_path == Path.home() / "acervus.db"

    @staticmethod
    def test_every_home_relative_root_is_expanded() -> None:
        config = AcervusConfig(
            db_path=Path("/var/acervus.db"),
            roots={"docs": Path("~/docs"), "photos": Path("~/pictures")},
        )

        assert config.roots == {
            "docs": Path.home() / "docs",
            "photos": Path.home() / "pictures",
        }

    @staticmethod
    def test_an_absolute_path_is_left_as_written() -> None:
        config = AcervusConfig(
            db_path=Path("/var/acervus.db"), roots={"docs": Path("/srv/docs")}
        )

        assert config.db_path == Path("/var/acervus.db")
        assert config.roots == {"docs": Path("/srv/docs")}


class TestWhatIsNotIndexed:
    @staticmethod
    def test_a_config_that_says_nothing_ignores_the_usual_machinery() -> None:
        config = AcervusConfig(db_path=Path("/var/acervus.db"), roots={})

        assert config.ignore == DEFAULT_IGNORE
        assert VENV in config.ignore

    @staticmethod
    def test_naming_patterns_replaces_the_defaults() -> None:
        config = AcervusConfig(
            db_path=Path("/var/acervus.db"), roots={}, ignore=("*.tmp",)
        )

        assert config.ignore == ("*.tmp",)

    @staticmethod
    def test_an_empty_list_ignores_nothing() -> None:
        config = AcervusConfig(db_path=Path("/var/acervus.db"), roots={}, ignore=())

        assert not config.ignore
