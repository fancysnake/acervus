"""Config loading for Acervus."""

import tomllib
from pathlib import Path

from acervus.pacts.config import AcervusConfig, ConfigFile

DEFAULT_CONFIG_PATH = Path("~/.config/acervus/config.toml")


def load_config(path: Path | None = None) -> AcervusConfig | None:
    """Read the config file, or report that there is none to read.

    A file that is there but malformed raises rather than returning ``None``:
    ``tomllib.TOMLDecodeError`` if it does not parse, a Pydantic validation
    error naming what is wrong if it parses into the wrong shape. Neither is
    swallowed here, so the entry point can name the file that is at fault.

    Returns:
        The configuration, or ``None`` if no file sits at the path.
    """
    config_path = (path or DEFAULT_CONFIG_PATH).expanduser()
    if not config_path.exists():
        return None
    with config_path.open("rb") as f:
        return ConfigFile.model_validate(tomllib.load(f)).acervus  # type: ignore [misc]
