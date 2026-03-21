"""CLI commands for Acervus."""

from __future__ import annotations

import click


def register_commands(cli: click.Group) -> None:
    """Register all CLI commands on the given group."""
    cli.add_command(status)


@click.command()
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
