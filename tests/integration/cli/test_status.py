"""Integration tests for acre status command."""

from __future__ import annotations

from click.testing import CliRunner

from acervus.inits import cli

SAMPLE_TOML = """\
[acervus]
db_path = "{db_path}"

[acervus.roots]
docs = "{docs_path}"
"""

SAMPLE_ALIAS = "docs"
NO_ROOTS_MESSAGE = "No roots configured"


class TestStatusCommand:
    @staticmethod
    def test_displays_config(tmp_path):
        docs_path = tmp_path / SAMPLE_ALIAS
        docs_path.mkdir()
        db_path = tmp_path / "acervus.db"

        config_path = tmp_path / "config.toml"
        config_path.write_text(SAMPLE_TOML.format(db_path=db_path, docs_path=docs_path))

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])

        assert result.exit_code == 0
        assert str(db_path) in result.output
        assert SAMPLE_ALIAS in result.output
        assert str(docs_path) in result.output

    @staticmethod
    def test_no_roots(tmp_path):
        db_path = tmp_path / "acervus.db"
        config_path = tmp_path / "config.toml"
        config_path.write_text(f'[acervus]\ndb_path = "{db_path}"\n\n[acervus.roots]\n')

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])

        assert result.exit_code == 0
        assert NO_ROOTS_MESSAGE in result.output
