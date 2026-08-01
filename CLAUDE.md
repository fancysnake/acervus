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
| **specs** | pacts                       | pure business invariants — `specs/mark.py` holds the mark name rules |
| **mills** | pacts, specs                | pure business logic; dependencies via constructor |
| **links** | pacts                       | data access — SQLAlchemy models, engine, repositories |
| **gates** | pacts                       | entry points — the Textual TUI                    |
| **inits** | pacts, specs, mills, links, gates | config loading, DI, the `main()` entry point |
| **edges** | nothing                     | infrastructure boundary (currently empty)         |

Three consequences carry the weight. **Only `inits` may wire `links` and `gates` together** — gates and mills cannot import `links` at all, so a TUI screen can never touch a SQLAlchemy model; it receives DTOs and services handed down from `inits`. **Neither `gates` nor `links` may import `mills`** — both are typed against protocols in `pacts` and receive concrete implementations by injection, so nothing at the edge names a concrete service. And **`specs` is for `mills` to call** — it holds pure business invariants, not configuration. `inits` is permitted to import it only because the contracts count indirect chains: wiring a service that validates through `specs` makes `inits → mills → specs` reachable, so forbidding it would forbid `specs` from being used at all. Nothing in `inits` should name a `specs` module directly. `AcervusConfig` lives in `pacts` because it is a data contract crossing inits → gates. `edges` is outside the import graph; nothing may import it.

Seven `inside-*` independence contracts sit on top of the seven layer contracts. The ones with teeth are `inside-pacts` and `inside-mills`: **sibling modules inside `pacts` and inside `mills` may not import each other**, so every noun module stands alone. A pacts module may be named after a port rather than a noun when its contract belongs to the port (`pacts/config.py`, `pacts/transaction.py`, `pacts/filesystem.py`).

### Slicing

`pacts`, `mills` and `specs` slice by **noun** (root, file, mark, stack), and `pacts` and `mills` must mirror each other. A pacts noun module holds every contract for that noun together — DTO, write TypedDict, repository protocol, errors. Do not create `pacts/dtos.py` or `pacts/protocols.py`; that slices by technical kind.

`links` slices `{port}/{adapter}/{kind}` (`links/db/sqlalchemy/models.py`), `gates` slices `{port}/{adapter}/{page}` (`gates/tui/textual/app.py`). The `links/db/sqlalchemy/__init__.py` facade is the adapter's public surface and re-exports exactly what `inits` injects into services — the repositories and the transaction, each backed by a protocol in `pacts`. Models, the declarative base, the engine and the session stay internal. Every other `__init__.py` stays empty; import symbols from the module that defines them.

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
