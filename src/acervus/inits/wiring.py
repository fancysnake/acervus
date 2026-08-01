"""Application entry point — loads config, builds the container, runs the TUI."""

from __future__ import annotations

import sys

from acervus.gates.tui.textual.app import AcervusApp
from acervus.inits.config import load_config
from acervus.inits.repositories import Repositories
from acervus.inits.services import Services

NO_CONFIG_MESSAGE = (
    "No config found. Create ~/.config/acervus/config.toml"
    " (see config.example.toml).\n"
)


def main() -> None:
    """Load config, reconcile the roots it names, and run the Acervus TUI."""
    if (config := load_config()) is None:
        sys.stderr.write(NO_CONFIG_MESSAGE)
        sys.exit(1)
    services = Services(Repositories(config.db_path))
    services.roots.sync(config.roots)
    AcervusApp(services.roots, services.scan).run()
