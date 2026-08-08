"""Config loading for Acervus."""

import tomllib
from pathlib import Path
from typing import cast

from acervus.pacts.config import AcervusConfig, ConfigFile

DEFAULT_CONFIG_PATH = Path("~/.config/acervus/config.toml")


def load_config(path: Path | None = None) -> AcervusConfig | None:
    """Read the config file, or report that there is none to read.

    A file that is there but malformed raises a Pydantic validation error
    naming what is wrong, rather than a bare ``KeyError`` for the section.

    Returns:
        The configuration, or ``None`` if no file sits at the path.
    """
    config_path = (path or DEFAULT_CONFIG_PATH).expanduser()
    if not config_path.exists():
        return None
    with config_path.open("rb") as f:
        data = cast("dict[str, object]", tomllib.load(f))
    return ConfigFile.model_validate(data).acervus
