# Acervus

A terminal **filesystem tagging tool** (in the spirit of [TMSU](https://tmsu.org/)).
Acervus organizes files across your disk with **marks** (labels) and **stacks**
(named groups), keeping the index in a local SQLite database while your files
stay exactly where they are.

> **Status:** MVP complete. Acervus scans your configured roots, browses the
> indexed files, and marks and stacks them from the TUI, with filtering on each.
> [`FEATURE_PLAN.md`](FEATURE_PLAN.md) records how it was built.

## Concepts

| Term      | Meaning                                                              |
|-----------|---------------------------------------------------------------------|
| **root**  | A named directory (`alias -> path`) that Acervus indexes.           |
| **file**  | A file discovered under a root, tracked by its path relative to it. |
| **mark**  | A label attached to files (many-to-many).                           |
| **stack** | A named group a file can belong to.                                 |

Naming: **acervus** is the project, **acre** is the installed command, **mark**
is a label, **stack** is a file group.

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

This exposes the `acre` command (entry point `acervus.inits.wiring:main`).

## Configuration

Acervus reads a TOML config from `~/.config/acervus/config.toml`.

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
acre                 # launch the TUI
```

The app opens on the roots screen, listing each configured `alias -> path`.

| Key | Where | Does |
|-----|-------|------|
| `f` / `m` / `t` | anywhere | Open the files, marks or stacks screen |
| `q` | anywhere | Quit |
| `s` | roots | Scan the root under the cursor and report what changed |
| `r` / `k` / `c` | files | Cycle the filter by root, by mark, by stack |
| `a` / `x` | files | Put a mark on the file under the cursor, take one off |
| `s` / `u` | files | Put the file in a stack, take it out of its stack |
| `escape` | any screen | Back |

A scan inserts files the root has and the index lacks, rewrites those whose size
or mtime moved, and drops those the root no longer has. Marks and stacks come
into being by being applied, and are deleted once nothing carries or sits in
them.

## Architecture

Acervus follows the **GLIMPSE** layered architecture, with import boundaries
enforced by [`import-linter`](https://import-linter.readthedocs.io/):

| Layer     | Responsibility                                              |
|-----------|-------------------------------------------------------------|
| **pacts** | Protocols, DTOs, dataclasses, exceptions (no dependencies). |
| **specs** | Pure business invariants, for `mills` only.                 |
| **mills** | Pure business logic; takes dependencies via constructor.    |
| **links** | Data access — SQLAlchemy models, engine, repositories.      |
| **gates** | Entry points — the Textual TUI.                             |
| **inits** | Config loading, dependency injection, the `main()` entry point. |
| **edges** | Infrastructure boundary.                                    |

Only `inits` may wire `links` and `gates` together, and `specs` is reachable from
`mills` alone. See [`CLAUDE.md`](CLAUDE.md) for the full layer rules and
conventions.

### Source layout

```text
src/acervus/
  pacts/               # protocols, DTOs, exceptions, AcervusConfig
  specs/               # business invariants
  mills/               # business logic
  links/db/sqlalchemy/ # models, engine, repositories, transaction
  links/fs/            # the pathlib filesystem reader
  gates/tui/textual/   # the Textual app and its screens
  inits/               # config loading, DI, the entry point
  edges/               # infrastructure
```

## Development

Tasks come from [`mise.toml`](mise.toml) and the shared config it includes over
git. `mise tasks ls --all` lists them.

```bash
mise run test:py            # all tests
mise run test:unit          # unit tests only
mise run test:int           # integration tests only
mise run lint:py            # every linter at once — what CI runs
mise run lint:ruff          # ruff, --no-fix
mise run lint:mypy          # mypy src (strict)
mise run lint:import-linter # GLIMPSE layer contracts
mise run lint:pylint src
mise run lint:codespell
mise run format:py          # black, ruff --fix and taplo
```

Pass extra arguments through with `--`, which is how you run a single test:

```bash
mise run test:unit -- -k test_it_trims_surrounding_whitespace
```

Tooling: **Black** (line length 88, preview), **Ruff** (`select = ["ALL"]`,
preview), **MyPy** (strict), **Import Linter**, **Pylint**, **Codespell**. Unit
tests mirror `src/` and stay IO-free; integration tests exercise `links`, `gates`
and the entry point against real infrastructure.

## License

BSD 3-Clause. See [`LICENSE`](LICENSE).
