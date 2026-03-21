"""Dependency injection container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acervus.specs import AcervusConfig


@dataclass
class DependencyInjector:
    config: AcervusConfig
