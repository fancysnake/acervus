"""Application entry point — loads config, builds the container, runs the TUI."""

import sys
from contextlib import closing

from acervus.gates.tui.textual.app import AcervusApp
from acervus.inits.config import load_config
from acervus.inits.repositories import Repositories
from acervus.inits.services import Services

NO_CONFIG_MESSAGE = (
    "No config found. Create ~/.config/acervus/config.toml"
    " (see config.example.toml).\n"
)


def build_app(services: Services) -> AcervusApp:
    """Hand the TUI the service protocols its screens need.

    Returns:
        An app ready to run, holding no container and no configuration.
    """
    return AcervusApp(
        roots=services.roots,
        scan=services.scan,
        files=services.files,
        marks=services.marks,
        stacks=services.stacks,
    )


def main() -> None:
    """Load config, reconcile the roots it names, and run the Acervus TUI."""
    if (config := load_config()) is None:
        sys.stderr.write(NO_CONFIG_MESSAGE)
        sys.exit(1)
    with closing(Repositories(config.db_path)) as repositories:
        services = Services(repositories)
        services.roots.sync(config.roots)
        build_app(services).run()
