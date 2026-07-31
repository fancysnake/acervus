# Acervus

A command-line **filesystem tagging tool** (in the spirit of [TMSU](https://tmsu.org/)).
Acervus organizes files across your disk with **marks** (labels) and **stacks**
(named groups), keeping the index in a local SQLite database while your files
stay exactly where they are.

> **Status:** early MVP. The database schema and CLI scaffolding are in place;
> the `status` command works today. Scanning, tagging, and query commands are
> under active development (see [`FEATURE_PLAN.md`](FEATURE_PLAN.md)).

## Concepts

| Term      | Meaning                                                              |
|-----------|---------------------------------------------------------------------|
| **root**  | A named directory (`alias -> path`) that Acervus indexes.           |
| **file**  | A file discovered under a root, tracked by its path relative to it. |
| **mark**  | A label attached to files (many-to-many).                           |
| **stack** | A named group a file can belong to.                                 |

Naming: **acervus** is the project, **acre** is the CLI command, **mark** is a
label, **stack** is a file group.

## Requirements

- Python **3.14+**
- [Poetry](https://python-poetry.org/) for dependency management
- [mise](https://mise.jdx.dev/) for tooling and task running

## Installation

```bash
# Install the toolchain and dependencies (mise reads mise.toml / pyproject.toml)
mise install
poetry install
```

This exposes the `acre` command (entry point `acervus.inits:cli`).

## Configuration

Acervus reads a TOML config from `~/.config/acervus/config.toml` by default.
Point at a different file with `acre --config path/to/config.toml`.

See [`config.example.toml`](config.example.toml):

```toml
[acervus]
db_path = "~/.local/share/acervus/acervus.db"

[acervus.roots]
# docs   = "/home/user/docs"
# photos = "/home/user/photos"
```

- `db_path` — where the SQLite index lives.
- `[acervus.roots]` — the named directories Acervus manages (`alias = "path"`).

If no config file is found, `acre` prints a hint and exits.

## Usage

```bash
acre --help          # list commands
acre --version       # print version
acre status          # show the configured database path and roots
```

Example `acre status` output:

```
Database: ~/.local/share/acervus/acervus.db
Roots:
  docs: /home/user/docs
  photos: /home/user/photos
```

Planned commands (per the MVP plan): `scan`, `files`, `mark`, `stack`.

## Architecture

Acervus follows the **GLIMPSE** layered architecture, with import boundaries
enforced by [`import-linter`](https://import-linter.readthedocs.io/):

| Layer     | Responsibility                                              |
|-----------|-------------------------------------------------------------|
| **pacts** | Protocols, DTOs, dataclasses, exceptions (no dependencies). |
| **specs** | Configuration models (`AcervusConfig`).                     |
| **mills** | Pure business logic; takes dependencies via constructor.    |
| **links** | Data access — SQLAlchemy models, engine, repositories.      |
| **gates** | Entry points — the Click CLI commands.                      |
| **inits** | Dependency injection and wiring; builds the `cli` group.    |
| **edges** | Infrastructure boundary.                                    |

Only `inits` may wire `specs`, `links`, and `gates` together. See
[`CLAUDE.md`](CLAUDE.md) for the full layer rules and conventions.

### Source layout

```
src/acervus/
  pacts/         # protocols, DTOs, exceptions
  specs/         # AcervusConfig
  mills/         # business logic
  links/db/      # SQLAlchemy models, engine, (repositories)
  gates/cli/     # Click commands
  inits/         # config loading, DI, CLI wiring (entry point)
  edges/         # infrastructure
```

## Development

Tasks are defined in [`mise.toml`](mise.toml):

```bash
mise run check      # format (black) + lint (ruff, mypy, import-linter, pylint, codespell)
mise run test       # run all tests
mise run unittest   # run unit tests only
mise run p <cmd>    # run poetry <cmd>
```

Tooling: **Black** (line length 88, preview), **Ruff** (`select = ["ALL"]`,
preview), **MyPy** (strict), **Import Linter**, **Pylint**, **Codespell**,
**Deptry**. Tests use **pytest** (unit tests mirror `src/`; integration tests
exercise the CLI).

## License

BSD 3-Clause. See [`LICENSE`](LICENSE).
