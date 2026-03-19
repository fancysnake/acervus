"""Pacts dataclasses — value objects for filesystem operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class FileInfo:
    relative_path: Path
    size: int
    mtime: float


@dataclass(frozen=True)
class ScanResult:
    added: int
    removed: int
    updated: int
