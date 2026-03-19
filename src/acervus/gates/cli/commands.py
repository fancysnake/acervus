"""CLI commands for Acervus."""

import click

from acervus import __version__


@click.group()
@click.version_option(version=__version__, prog_name="acre")
def cli() -> None:
    """Acervus — filesystem tagging tool."""
