"""Configuration contract for Acervus."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AcervusConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    db_path: Path
    roots: dict[str, Path]
