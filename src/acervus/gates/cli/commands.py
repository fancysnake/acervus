"""CLI commands for Acervus."""

from __future__ import annotations

from pathlib import Path

import click

from acervus import __version__
from acervus.mills.config import load_config


@click.group()
@click.version_option(version=__version__, prog_name="acre")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None) -> None:
    """Acervus — filesystem tagging tool."""
    ctx.ensure_object(dict)
    if (config := load_config(config_path)) is None:
        click.echo(
            "No config found. Create ~/.config/acervus/config.toml"
            " (see config.example.toml).",
        )
        ctx.exit(1)
    ctx.obj["config"] = config


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current configuration and status."""
    config = ctx.obj["config"]

    click.echo(f"Database: {config.db_path}")

    if not config.roots:
        click.echo("No roots configured.")
        return

    click.echo("Roots:")
    for alias, path in config.roots.items():
        click.echo(f"  {alias}: {path}")
