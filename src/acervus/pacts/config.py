"""Configuration contract for Acervus."""

from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

# A path a person wrote, so ``~`` means their home rather than a directory of
# that name. Expanded on the way in, so nothing downstream has to remember to.
type UserPath = Annotated[Path, AfterValidator(Path.expanduser)]

# The machinery of tools that live inside a tree rather than beside it. Naming
# ``ignore`` in the config replaces this list rather than adding to it.
DEFAULT_IGNORE: tuple[str, ...] = (".git", ".venv", "node_modules", "__pycache__")


class AcervusConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    db_path: UserPath
    roots: dict[str, UserPath]
    # Glob patterns matched against one path component at a time, so ``.venv``
    # skips a directory of that name at any depth and ``*.pyc`` skips a file.
    ignore: tuple[str, ...] = DEFAULT_IGNORE


class ConfigFile(BaseModel):
    """A config file as it is written on disk, under its ``[acervus]`` table."""

    acervus: AcervusConfig
