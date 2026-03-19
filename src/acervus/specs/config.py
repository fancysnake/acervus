"""Specs — configuration model for Acervus."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class AcervusConfig(BaseModel):
    db_path: Path
    roots: dict[str, Path]
