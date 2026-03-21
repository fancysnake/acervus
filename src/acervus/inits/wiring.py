"""CLI wiring — creates the cli group with config loading and DI."""

from __future__ import annotations

from pathlib import Path

import click

from acervus import __version__
from acervus.gates.cli.commands import register_commands
from acervus.inits.config import load_config
from acervus.inits.di import DependencyInjector


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
    ctx.obj["di"] = DependencyInjector(config=config)


register_commands(cli)
