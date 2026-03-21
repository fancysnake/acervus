"""Dependency injection and application wiring."""

from acervus.inits.di import DependencyInjector
from acervus.inits.wiring import cli

__all__ = ["DependencyInjector", "cli"]
