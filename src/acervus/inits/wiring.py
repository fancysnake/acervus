"""Application entry point — loads config and launches the Textual app."""

from __future__ import annotations

import sys

from acervus.gates.tui.textual.app import AcervusApp
from acervus.inits.config import load_config

NO_CONFIG_MESSAGE = (
    "No config found. Create ~/.config/acervus/config.toml"
    " (see config.example.toml).\n"
)


def main() -> None:
    """Load config and run the Acervus TUI, or exit if no config exists."""
    if (config := load_config()) is None:
        sys.stderr.write(NO_CONFIG_MESSAGE)
        sys.exit(1)
    AcervusApp(db_path=config.db_path, roots=config.roots).run()
