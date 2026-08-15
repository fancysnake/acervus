# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Acervus is a filesystem tagging tool (in the spirit of TMSU): it indexes files under named **roots** and organizes them with **marks** (labels, many-to-many) and **stacks** (a file belongs to at most one). Files stay where they are; the index lives in a local SQLite database.

Naming: **acervus** = project, **acre** = the installed command, **mark** = label, **stack** = file group.

Python 3.14, Poetry for dependencies, mise for tooling and tasks.

## State of the repo

The MVP is complete. The entry point is `acervus.inits.wiring:main` (`pyproject.toml`), which loads config, reconciles the configured roots against the index, and launches a **Textual TUI** (`acervus.gates.tui.textual.app.AcervusApp`). Click is not a dependency; `textual` is.

Every layer but `edges` is populated. `pacts` holds the contracts for four nouns (`root`, `file`, `mark`, `stack`) alongside the `config`, `transaction` and `filesystem` ports. `specs` holds the mark and stack name invariants. `mills` holds four services — `RootService`, `ScanService`, `MarkService`, `StackService`. There is no file service: reading files carries no business rule, so the screens read through `FileRepositoryProtocol`, and adding one back is only worth it when a rule turns up to live in it. `links` holds the SQLAlchemy models, engine, repositories and transaction, plus the pathlib filesystem reader at `links/fs/pathlib/reader.py`. `gates` holds four TUI screens (roots, files, marks, stacks) and one modal name prompt. `inits` holds `load_config`, the `Repositories` / `Services` containers, and `IsolatedScan`, which gives a scan a session of its own so the roots screen can run it on a thread. The TUI receives services — no config and no container cross that boundary.

Integrity is the database's: every foreign key declares `ondelete`, and `open_database` switches `foreign_keys` on (and `journal_mode=WAL`, so the interface reading does not block a scan writing). Deleting a root, a mark or a stack is one statement; nothing hand-rolls a cascade.

`FEATURE_PLAN.md` records how it was built, step by step. Every step in it is done; it is history, not a to-do list.

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
mise run lint:py         # every linter at once, plus black --check, taplo and vulture
mise run format:black    # black src tests
mise run format:ruff     # ruff --fix
mise run format:py       # both of the above, plus taplo
```

Pass extra arguments through with `--`, which is how you run a single test:

```bash
mise run test:unit -- -k test_it_trims_surrounding_whitespace
```

Every task comes from the shared config that `mise.toml` includes over git; `mise tasks ls --all` lists what is actually available. `lint:py` is the gate CI runs and it passes clean, so prefer it over invoking the linters one by one.

## Architecture: GLIMPSE layers

Seven layers, with import direction enforced by import-linter contracts in `pyproject.toml` (`mise run lint:import-linter`). A change that violates the table fails the build.

| Layer     | CAN import                  | Holds                                             |
|-----------|-----------------------------|---------------------------------------------------|
| **pacts** | nothing                     | protocols, Pydantic DTOs, frozen dataclasses, exceptions — including `AcervusConfig` |
| **specs** | pacts                       | pure business invariants — `specs/mark.py` holds the mark name rules |
| **mills** | pacts, specs                | pure business logic; dependencies via constructor |
| **links** | pacts                       | data access — SQLAlchemy models, engine, repositories |
| **gates** | pacts                       | entry points — the Textual TUI                    |
| **inits** | pacts, mills, links, gates, and specs only through mills | config loading, DI, the `main()` entry point |
| **edges** | nothing                     | infrastructure boundary (currently empty)         |

Three consequences carry the weight. **Only `inits` may wire `links` and `gates` together** — gates and mills cannot import `links` at all, so a TUI screen can never touch a SQLAlchemy model; it receives DTOs and services handed down from `inits`. **Neither `gates` nor `links` may import `mills`** — both are typed against protocols in `pacts` and receive concrete implementations by injection, so nothing at the edge names a concrete service. And **`specs` is for `mills` to call** — it holds pure business invariants, not configuration. `inits` is permitted to import it only because the contracts count indirect chains: wiring a service that validates through `specs` makes `inits → mills → specs` reachable, so forbidding it would forbid `specs` from being used at all. No module in `inits` may name a `specs` module directly, and the `inits-specs-only-through-mills` contract (`allow_indirect_imports`) fails the build if one does. `AcervusConfig` lives in `pacts` because it is a data contract crossing inits → gates. `edges` is outside the import graph; nothing may import it.

Seven `inside-*` independence contracts sit on top of the seven layer contracts. The ones with teeth are `inside-pacts` and `inside-mills`: **sibling modules inside `pacts` and inside `mills` may not import each other**, so every noun module stands alone. A pacts module may be named after a port rather than a noun when its contract belongs to the port (`pacts/config.py`, `pacts/transaction.py`, `pacts/filesystem.py`).

### Slicing

`pacts`, `mills` and `specs` slice by **noun** (root, file, mark, stack), and `pacts` and `mills` must mirror each other. A pacts noun module holds every contract for that noun together — DTO, write TypedDict, repository protocol, errors. Do not create `pacts/dtos.py` or `pacts/protocols.py`; that slices by technical kind.

`links` slices `{port}/{adapter}/{kind}` (`links/db/sqlalchemy/models.py`), `gates` slices `{port}/{adapter}/{page}` (`gates/tui/textual/app.py`). The `links/db/sqlalchemy/__init__.py` facade is the adapter's public surface and re-exports exactly what `inits` injects into services — the repositories and the transaction, each backed by a protocol in `pacts`. Models, the declarative base, the engine and the session stay internal. Every other `__init__.py` stays empty; import symbols from the module that defines them.

Repositories implement a protocol declared in `pacts`, declare it as a base class, and return Pydantic DTOs (`ConfigDict(from_attributes=True)`), never ORM models. Services take the specific repository protocols they use plus a `TransactionProtocol` by constructor — there is no Unit of Work.

## Type checking

MyPy runs strict *plus* `disallow_any_expr` and `disallow_any_decorated`. Those two are relaxed per-module in `pyproject.toml` for `acervus.gates.tui.textual.*`, `acervus.inits.wiring`, and `acervus.links.db.*` — the packages where third-party code leaks `Any`. When you add a module that wraps Textual or SQLAlchemy, expect to either keep `Any` out of the signatures or extend that override list.

Ruff runs `select = ["ALL"]` in preview mode, ignoring only `CPY` and `D1`. Tests additionally waive `ANN` and `S`.

## Testing

The layer under test dictates the test type. Both trees mirror `src/`, down to the adapter (`tests/integration/links/db/sqlalchemy/repositories/test_mark.py`); `tests/integration/` covers everything that touches IO. `asyncio_mode = "auto"`, so async tests need no marker.

- Group tests in classes; test methods are `@staticmethod`, and take their fixtures **keyword-only** (`def test_x(*, roots, files)`). Pytest fills fixtures in by name, so keyword-only says what is happening and keeps the positional-argument limit meaningful without a `pylint: disable`.
- An integration test of a screen proves the keystroke reaches the service and the screen redraws. What the service then does is settled in its `tests/unit/mills/` test — do not assert it again through a pilot.
- Unit tests cover `mills`, `pacts`, `specs` and pure functions — no filesystem, no database, no entry points. Mock at the highest level and assert every mock call.
- Integration tests cover `links`, `gates` and the IO-bearing parts of `inits`, against real infrastructure: repositories against a real SQLite file, the TUI via Textual's `app.run_test()` pilot. Test repositories directly, not only through a screen.
- Never raise coverage on an IO-bearing layer with a mock-everything unit test.
- Spell out magic numbers with an arithmetic comment: `assert len(config.roots) == 1 + 1  # docs + photos`.

## Conventions

- A screen's `compose` yields the same widget tree every time and reads nothing; data is loaded in `on_mount` and an empty state is a `display` toggle, so `query_one` never depends on what came back.
- Never add `noqa`, `type: ignore`, `pylint`, or `pragma` directives without explicit per-case approval.
- Never modify, create, or delete configuration files without explicit per-case approval.
