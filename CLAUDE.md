# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Acervus is a filesystem tagging tool (in the spirit of TMSU): it indexes files under named **roots** and organizes them with **marks** (labels, many-to-many) and **stacks** (a file belongs to at most one). Files stay where they are; the index lives in a local SQLite database.

Naming: **acervus** = project, **acre** = the installed command, **mark** = label, **stack** = file group.

Python 3.14, Poetry for dependencies, mise for tooling and tasks.

## State of the repo (read before trusting the docs)

The project is an early MVP and **`README.md` and `FEATURE_PLAN.md` are stale**. Both describe a Click CLI with an `acre status` command and entry point `acervus.inits:cli`. That code has been deleted. The actual entry point is `acervus.inits:main` (`pyproject.toml`), which loads config and launches a **Textual TUI** (`acervus.gates.tui.textual.app.AcervusApp`). Click is not a dependency; `textual` is.

Consequently `links/` has models and an engine but no repositories, `mills/` is empty, and the `UnitOfWorkProtocol` / `*RepositoryProtocol` in `pacts/protocols.py` have no implementations yet. `DependencyInjector` currently holds only a config, and the TUI receives `db_path`/`roots` directly rather than through a unit of work.

## Commands

Never run `python`, `pytest`, or `mypy` directly — mise owns the virtualenv.

```bash
mise run test:unit       # unit tests
mise run test:int        # integration tests
mise run test:py         # both
mise run lint:ruff       # ruff, --no-fix
mise run lint:mypy       # mypy src (strict)
mise run lint:import-linter   # GLIMPSE layer contracts
mise run lint:pylint src
mise run lint:codespell
mise run format:black    # black src tests
mise run format:ruff     # ruff --fix
mise run p <cmd>         # run poetry <cmd>
```

Run a single test through poetry:

```bash
mise run p run pytest tests/unit/specs/test_config.py -k test_empty_roots
```

### Broken aggregate tasks

`python_tasks.toml` was copied from a Django project and several tasks reference tooling this repo does not have. **Do not reach for them; run the individual `lint:*` / `format:*` / `test:*` tasks above instead.**

- `check`, `devcheck`, `fullcheck` — depend on a task named `lint`, but the file defines `_lint`; mise errors out.
- `format`, `_lint` — invoke `djlint` and `vulture`, neither of which is installed.
- `shitcheck` — calls `scripts/shitcheck.sh`; there is no `scripts/` directory.
- `test:*:cov:diff` — reference `acervus.adapters.web`, a package that does not exist.

`lint:ruff` currently fails on pre-existing `COM812` (missing trailing comma) findings. Black runs with `skip-magic-trailing-comma`, so `format:black` strips commas that ruff then demands; running `format:ruff` after black settles it.

## Architecture: GLIMPSE layers

Seven layers, with import direction enforced by import-linter contracts in `pyproject.toml` (`mise run lint:import-linter`). A change that violates the table fails the build.

| Layer     | CAN import                        | Holds                                             |
|-----------|-----------------------------------|---------------------------------------------------|
| **pacts** | nothing                           | protocols, Pydantic DTOs, frozen dataclasses, exceptions |
| **specs** | pacts                             | configuration models (`AcervusConfig`)            |
| **mills** | pacts                             | pure business logic; dependencies via constructor |
| **links** | pacts, mills                      | data access — SQLAlchemy models, engine, repositories |
| **gates** | pacts, mills                      | entry points — the Textual TUI                    |
| **inits** | pacts, specs, mills, links, gates | config loading, DI, the `main()` entry point      |
| **edges** | nothing                           | infrastructure boundary (currently empty)         |

The load-bearing consequence: **only `inits` may wire `specs`, `links`, and `gates` together.** Gates and mills cannot import `links` or `specs` at all, so a TUI screen can never touch a SQLAlchemy model or read config directly — it receives DTOs and plain values handed down from `inits`. `edges` is outside the import graph; nothing imports it.

Repositories, when written, implement a protocol declared in `pacts` and return Pydantic DTOs (`ConfigDict(from_attributes=True)`), never ORM models. The DTO field sets in `pacts/dtos.py` mirror the models in `links/db/models.py`.

## Type checking

MyPy runs strict *plus* `disallow_any_expr` and `disallow_any_decorated`. Those two are relaxed per-module in `pyproject.toml` for `acervus.gates.tui.textual.*`, `acervus.inits.wiring`, and `acervus.links.db.*` — the packages where third-party code leaks `Any`. When you add a module that wraps Textual or SQLAlchemy, expect to either keep `Any` out of the signatures or extend that override list.

Ruff runs `select = ["ALL"]` in preview mode, ignoring only `CPY` and `D1`. Tests additionally waive `ANN` and `S`.

## Testing

`tests/unit/` mirrors `src/`; `tests/integration/` exercises entry points. `asyncio_mode = "auto"`, so async tests need no marker.

- Group tests in classes; test methods are `@staticmethod`.
- Unit tests cover mills, pacts, specs, and functions — no database, no entry points.
- Integration tests cover the TUI via Textual's `app.run_test()` pilot. Repositories are not tested directly; they are covered through integration tests.
- Spell out magic numbers with an arithmetic comment: `assert len(config.roots) == 1 + 1  # docs + photos`.

## Conventions

- Never add `noqa`, `type: ignore`, `pylint`, or `pragma` directives without explicit per-case approval.
- Never modify, create, or delete configuration files without explicit per-case approval.
