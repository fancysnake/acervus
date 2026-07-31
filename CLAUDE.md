# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Acervus is a filesystem tagging tool (in the spirit of TMSU): it indexes files under named **roots** and organizes them with **marks** (labels, many-to-many) and **stacks** (a file belongs to at most one). Files stay where they are; the index lives in a local SQLite database.

Naming: **acervus** = project, **acre** = the installed command, **mark** = label, **stack** = file group.

Python 3.14, Poetry for dependencies, mise for tooling and tasks.

## State of the repo

The project is an early MVP. The entry point is `acervus.inits.wiring:main` (`pyproject.toml`), which loads config and launches a **Textual TUI** (`acervus.gates.tui.textual.app.AcervusApp`). Click is not a dependency; `textual` is.

What exists today: `pacts/config.py` (`AcervusConfig`), `inits/config.py` (`load_config`), `inits/wiring.py` (`main`), `links/db/sqlalchemy/{models,engine}.py`, and the TUI shell. What does not: `mills/` and `specs/` are empty, there are no repositories, no protocols, and no DI container — the TUI still receives `db_path`/`roots` directly instead of a services container. `FEATURE_PLAN.md` is the plan for closing that gap and is current.

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
mise run p run pytest tests/unit/pacts/test_config.py -k test_empty_roots
```

### Broken aggregate tasks

`python_tasks.toml` was copied from a Django project and several tasks reference tooling this repo does not have. **Do not reach for them; run the individual `lint:*` / `format:*` / `test:*` tasks above instead.**

- `check`, `devcheck`, `fullcheck` — depend on a task named `lint`, but the file defines `_lint`; mise errors out.
- `format`, `_lint` — invoke `djlint` and `vulture`, neither of which is installed.
- `shitcheck` — calls `scripts/shitcheck.sh`; there is no `scripts/` directory.
- `test:*:cov:diff` — reference `acervus.adapters.web`, a package that does not exist.

Black runs with `skip-magic-trailing-comma`, so `format:black` strips trailing commas that ruff then demands back as `COM812`. Run `format:ruff` after `format:black` to settle them.

## Architecture: GLIMPSE layers

Seven layers, with import direction enforced by import-linter contracts in `pyproject.toml` (`mise run lint:import-linter`). A change that violates the table fails the build.

| Layer     | CAN import                  | Holds                                             |
|-----------|-----------------------------|---------------------------------------------------|
| **pacts** | nothing                     | protocols, Pydantic DTOs, frozen dataclasses, exceptions — including `AcervusConfig` |
| **specs** | pacts                       | pure business invariants (empty until one exists) |
| **mills** | pacts, specs                | pure business logic; dependencies via constructor |
| **links** | pacts, mills                | data access — SQLAlchemy models, engine, repositories |
| **gates** | pacts, mills                | entry points — the Textual TUI                    |
| **inits** | pacts, mills, links, gates  | config loading, DI, the `main()` entry point      |
| **edges** | nothing                     | infrastructure boundary (currently empty)         |

Two consequences carry the weight. **Only `inits` may wire `links` and `gates` together** — gates and mills cannot import `links` at all, so a TUI screen can never touch a SQLAlchemy model; it receives DTOs and services handed down from `inits`. And **`specs` is reachable from `mills` alone** — it holds pure business invariants, not configuration. `AcervusConfig` lives in `pacts` because it is a data contract crossing inits → gates. `edges` is outside the import graph; nothing may import it.

### Slicing

`pacts`, `mills` and `specs` slice by **noun** (root, file, mark, stack), and `pacts` and `mills` must mirror each other. A pacts noun module holds every contract for that noun together — DTO, write TypedDict, repository protocol, errors. Do not create `pacts/dtos.py` or `pacts/protocols.py`; that slices by technical kind.

`links` slices `{port}/{adapter}/{kind}` (`links/db/sqlalchemy/models.py`), `gates` slices `{port}/{adapter}/{page}` (`gates/tui/textual/app.py`). The `links/db/sqlalchemy/__init__.py` facade is the adapter's public surface and re-exports repositories only — models, the declarative base and the engine stay internal. Every other `__init__.py` stays empty; import symbols from the module that defines them.

Repositories implement a protocol declared in `pacts`, declare it as a base class, and return Pydantic DTOs (`ConfigDict(from_attributes=True)`), never ORM models. Services take the specific repository protocols they use plus a `TransactionProtocol` by constructor — there is no Unit of Work.

## Type checking

MyPy runs strict *plus* `disallow_any_expr` and `disallow_any_decorated`. Those two are relaxed per-module in `pyproject.toml` for `acervus.gates.tui.textual.*`, `acervus.inits.wiring`, and `acervus.links.db.*` — the packages where third-party code leaks `Any`. When you add a module that wraps Textual or SQLAlchemy, expect to either keep `Any` out of the signatures or extend that override list.

Ruff runs `select = ["ALL"]` in preview mode, ignoring only `CPY` and `D1`. Tests additionally waive `ANN` and `S`.

## Testing

The layer under test dictates the test type. `tests/unit/` mirrors `src/`; `tests/integration/` covers everything that touches IO. `asyncio_mode = "auto"`, so async tests need no marker.

- Group tests in classes; test methods are `@staticmethod`.
- Unit tests cover `mills`, `pacts`, `specs` and pure functions — no filesystem, no database, no entry points. Mock at the highest level and assert every mock call.
- Integration tests cover `links`, `gates` and the IO-bearing parts of `inits`, against real infrastructure: repositories against a real SQLite file, the TUI via Textual's `app.run_test()` pilot. Test repositories directly, not only through a screen.
- Never raise coverage on an IO-bearing layer with a mock-everything unit test.
- Spell out magic numbers with an arithmetic comment: `assert len(config.roots) == 1 + 1  # docs + photos`.

## Conventions

- Never add `noqa`, `type: ignore`, `pylint`, or `pragma` directives without explicit per-case approval.
- Never modify, create, or delete configuration files without explicit per-case approval.
