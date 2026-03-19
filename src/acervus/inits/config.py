"""Config loading for Acervus."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from acervus.specs.config import AcervusConfig

DEFAULT_CONFIG_PATH = Path("~/.config/acervus/config.toml")


def load_config(path: Path | None = None) -> AcervusConfig:
    config_path = (path or DEFAULT_CONFIG_PATH).expanduser()
    with config_path.open("rb") as f:
        data = cast("dict[str, object]", tomllib.load(f))
    return AcervusConfig.model_validate(data["acervus"])
