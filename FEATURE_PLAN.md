# Acervus MVP Plan

## Context

Acervus is a filesystem tagging tool (like TMSU). It indexes files under named
**roots** and organizes them with **marks** (labels, many-to-many) and **stacks**
(a file belongs to at most one). Files stay where they are; the index lives in a
local SQLite database.

**Naming:** acervus (project), acre (the installed command), mark (label), stack
(file group).

Architecture: GLIMPSE layering, SQLAlchemy + SQLite, a Textual TUI. Entry point
`acervus.inits.wiring:main`.

## Import rules (enforced by `mise run lint:import-linter`)

| Layer | CAN import | CANNOT import |
|-------|-----------|---------------|
| pacts | nothing | gates, links, inits, mills, specs, edges |
| specs | pacts | gates, links, inits, mills, edges |
| mills | pacts, specs | gates, links, inits, edges |
| links | pacts | gates, inits, mills, specs, edges |
| gates | pacts | links, inits, mills, specs, edges |
| inits | pacts, mills, links, gates | specs, edges |
| edges | nothing | everything |

Three constraints do the load-bearing work.

**Only `inits` may wire `links` and `gates` together.** A TUI screen can never
touch a SQLAlchemy model; it receives DTOs and services handed down from `inits`.

**Neither `gates` nor `links` may import `mills`.** They are typed against
protocols in `pacts` and receive concrete implementations by injection. A screen
declares the service protocols it uses; a repository declares the repository
protocol it satisfies. Nothing at the edge names a concrete service.

**`specs` is reachable from `mills` alone** — it holds pure business invariants,
nothing else.

Seven `inside-*` independence contracts sit on top of these. The one with teeth
is `inside-pacts` / `inside-mills`: **sibling modules inside `pacts` and inside
`mills` may not import each other.** Each noun module stands alone. Two
consequences are baked into the layout below — `FileInfo` lives in
`pacts/filesystem.py` rather than `pacts/file.py`, and there is no
`pacts/services.py` container protocol.

## Target layout

| Layer | Modules |
|-------|---------|
| pacts | `config.py`, `root.py`, `file.py`, `mark.py`, `stack.py`, `transaction.py`, `filesystem.py` |
| specs | `mark.py`, `stack.py` (invariants only, as they appear) |
| mills | `root.py`, `file.py`, `mark.py`, `stack.py` |
| links | `db/sqlalchemy/{__init__,models,engine,repositories,transaction}.py`, `fs/pathlib.py` |
| gates | `tui/textual/{app,roots,files,marks,stacks}.py` |
| inits | `config.py`, `wiring.py`, `repositories.py`, `services.py` |
| tests | `tests/unit/{pacts,mills}/`, `tests/integration/{inits,links,tui}/` |

### Slicing

`pacts`, `mills` and `specs` slice **by noun** — root, file, mark, stack — and
`pacts` and `mills` must mirror each other. Each pacts noun module holds every
boundary contract for that noun together: its DTO, its write TypedDict, its
repository protocol, its service protocol, its errors. Not `pacts/dtos.py` or
`pacts/protocols.py` — that slices by technical kind, which is the thing to
avoid. Verb cuts (`pacts/file/scan.py`) come only when a noun actually gets fat.

A pacts module may also be named after a **port** rather than a noun when the
contract it holds belongs to the port: `pacts/transaction.py`,
`pacts/filesystem.py`, `pacts/config.py`. These are contracts that cross a
boundary without belonging to any one noun. `FileInfo` — what a filesystem
reader yields — therefore lives in `pacts/filesystem.py`, not `pacts/file.py`;
`FileDTO` and the file repository protocol stay in `pacts/file.py`. Since
`inside-pacts` forbids sibling imports, a port module and a noun module never
reach for each other.

There is deliberately **no `pacts/services.py`** container protocol. It would
have to name every noun's service protocol, which `inside-pacts` forbids.
Instead `inits` hands each screen the specific service protocols it uses, the
same interface segregation the services themselves follow.

`links` slices `{port}/{adapter}/{kind}`, `gates` slices `{port}/{adapter}/{page}`.
The `links/db/sqlalchemy/__init__.py` facade is the adapter's public surface: it
re-exports exactly the classes `inits` injects into services — the repositories
and the transaction — because each of those is named by a protocol in `pacts`.
Models, the declarative base, the engine and the session stay internal, so
external code writes `from acervus.links.db.sqlalchemy import RootRepository`
and never reaches `models`.

`__init__.py` files stay empty by default. The adapter facade above is the one
sanctioned exception; import every other symbol from the module that defines it.

### No Unit of Work

Services take the **specific repository protocols they use plus a
`TransactionProtocol`**, by constructor — `ScanService(files, roots, filesystem,
transaction)`, never `ScanService(uow)`. That is interface segregation at the
service boundary: a service declares the two or three ports it touches and
nothing more. Multi-repository writes go through `transaction.atomic()` inside
the service; a gate never opens a transaction. Every repository declares its
protocol as a base class so the type checker verifies conformance.

Repositories are exposed as flat `@cached_property` leaves on
`inits/repositories.py`, services likewise on `inits/services.py`. Four nouns is
far below the ~12-symbol threshold where bucketing starts to pay, so both stay
flat.

### Test type follows the layer

`mills` is pure logic — unit tests, no IO, mock at the highest level and assert
every mock call. `links`, `gates` and the IO-bearing parts of `inits` get
integration tests against real infrastructure: repositories against a real SQLite
file, the TUI through Textual's `app.run_test()` pilot. Repositories are tested
directly, not only through a screen. Never raise coverage on an IO-bearing layer
with a mock-everything unit test.

## Done

- **Config model** — `pacts/config.py`, `AcervusConfig(db_path, roots)`.
- **Config loading** — `inits/config.py`, `load_config()` over `tomllib`,
  default `~/.config/acervus/config.toml`, returns `None` when absent.
- **Entry point** — `inits/wiring.py`, `main()` loads config and launches the
  app, or exits 1 with a pointer to `config.example.toml`.
- **SQLAlchemy models and engine** — `links/db/sqlalchemy/{models,engine}.py`,
  `Root`, `File`, `Mark`, `FileMark`, `Stack`, plus `create_engine_from_path()`
  and `init_db()`.
- **TUI shell** — `gates/tui/textual/app.py`, lists the configured roots.

## Steps

Each step is TDD: write the test (red), implement (green), then
`mise run lint:ruff`, `lint:mypy`, `lint:import-linter`, `lint:pylint src` and
`mise run test:py` before committing.

---

### Step 1: pacts — the root and file nouns

**Tests first:** `tests/unit/pacts/test_root.py`, `tests/unit/pacts/test_file.py`,
`tests/unit/pacts/test_filesystem.py` — DTO validation and `from_attributes`
round-tripping.

**Files:**

- `pacts/root.py` — `RootDTO`, `RootWrite` TypedDict, `RootRepositoryProtocol`,
  `RootServiceProtocol`, `RootNotFoundError`
- `pacts/file.py` — `FileDTO`, `FileWrite`, `ScanResult` (added, removed,
  updated), `FileRepositoryProtocol`, `ScanServiceProtocol`, `FileMissingError`
- `pacts/filesystem.py` — `FileInfo` (frozen dataclass: relative_path, size,
  mtime) and `FilesystemReaderProtocol`
- `pacts/transaction.py` — `TransactionProtocol` with `atomic()`

`FileMissingError`, not `FileNotFoundError` — the latter shadows a builtin and
trips ruff `A001` and pylint `W0622`.

Every DTO carries `model_config = ConfigDict(from_attributes=True)` and mirrors
the corresponding model's field set. No module here imports a sibling.

---

### Step 2: links — root and file repositories

**Tests first:** `tests/integration/links/test_repositories.py` — against a real
SQLite file, not a mock.

**Files:**

- `links/db/sqlalchemy/repositories.py` — `RootRepository` (`list_all`, `read`,
  `read_by_alias`, `upsert_many`, `delete_many`) and `FileRepository`
  (`list_by_root`, `upsert_many`, `delete_many`), each declaring its protocol as
  a base class and returning DTOs, never ORM models
- `links/db/sqlalchemy/__init__.py` — re-export both repository classes

Repositories do plain data access. Reconciling the configured roots against the
database is business logic and belongs to the next step, not here.

---

### Step 3: mills — RootService.sync

**Tests first:** `tests/unit/mills/test_root.py` — mock `RootRepositoryProtocol`
and `TransactionProtocol`; assert every call.

**Files:** `mills/root.py` — `RootService(roots, transaction)` with
`sync(configured: dict[str, Path]) -> list[RootDTO]`, inserting roots new to the
config, dropping roots no longer in it, and updating changed paths — all inside
one `transaction.atomic()`.

This restores the `pacts/root.py` ↔ `mills/root.py` mirror the symmetry rule
requires.

---

### Step 4: the transaction adapter and the container

**Tests first:** `tests/integration/links/test_transaction.py` — against a real
SQLite file, that a clean exit commits and an exception rolls back.

**Files:**

- `links/db/sqlalchemy/transaction.py` — `SessionTransaction`, implementing
  `TransactionProtocol` over the session the repositories share: `atomic()`
  commits on clean exit and rolls back on exception
- `links/db/sqlalchemy/__init__.py` — re-export it alongside the repositories
- `inits/repositories.py` — engine creation, `init_db`, a session, and a
  `@cached_property` per repository and for the transaction
- `inits/services.py` — a `@cached_property` per service, flat

**Test:** `tests/integration/inits/test_wiring.py` — the container builds, the
database file is created, repositories and services are reachable.

The transaction is an adapter detail of the database port — it wraps the
session — so it lives in `links` next to the repositories that share that
session, and `inits` hands it to the services that need one. `inits` is the
only layer that names both a concrete repository and a concrete service, which
is exactly its job.

---

### Step 5: TUI — roots screen off a service

**Tests first:** extend `tests/integration/tui/test_app.py`.

**Files:**

- `gates/tui/textual/app.py` — takes `roots: RootServiceProtocol` instead of
  `db_path` / `roots: dict`
- `gates/tui/textual/roots.py` — the roots screen, rendering `RootDTO`s
- `inits/wiring.py` — builds the container and injects the service

Each screen takes the service protocols it uses and nothing more; there is no
container object crossing into `gates`. This is the step that closes the current
shortcut of passing raw config values into the TUI.

---

### Step 6: links — the filesystem adapter

**Tests first:** `tests/integration/links/test_filesystem.py` — a real temp
directory.

**Files:** `links/fs/pathlib.py` — `PathlibFilesystemReader` implementing
`FilesystemReaderProtocol`, yielding `FileInfo`.

---

### Step 7: mills — ScanService, insert only

**Tests first:** `tests/unit/mills/test_file.py` — mock the repository protocols
and the reader; assert every call.

**Files:** `mills/file.py` — `ScanService(files, roots, filesystem, transaction)`
with `scan(alias) -> ScanResult`.

---

### Step 8: TUI — scan action

**Files:** `gates/tui/textual/roots.py` — a binding that scans the selected root
and reports the `ScanResult`; `inits/services.py` gains the `scan` leaf.

---

### Step 9: mills — ScanService full diff

**Tests first:** extend `tests/unit/mills/test_file.py` with added, removed and
updated cases.

**Files:** `mills/file.py` — detect removals and mtime/size changes.

---

### Step 10: TUI — files screen

**Files:** `pacts/file.py` (list filters), `links/.../repositories.py`
(`FileRepository.list_all`), `gates/tui/textual/files.py` — files as
`alias:relative/path`, filterable by root.

---

### Step 11: marks — pacts, links, mills

**Tests first:** `tests/unit/pacts/test_mark.py`, `tests/unit/mills/test_mark.py`,
`tests/integration/links/test_repositories.py` extension.

**Files:** `pacts/mark.py`, `links/.../repositories.py` (`MarkRepository`),
`mills/mark.py` (`MarkService.add` / `.remove`), `specs/mark.py` if a name
invariant emerges (charset, length).

---

### Step 12: TUI — marks

**Files:** `gates/tui/textual/marks.py` — add and remove marks on the selected
file, list all marks with counts; `inits/services.py` gains the `mark` leaf.

---

### Step 13: TUI — filter files by mark

**Files:** `links/.../repositories.py` (mark filter), `gates/tui/textual/files.py`
— filter by mark, and an unmarked-only view.

---

### Step 14: stacks — pacts, links, mills

**Tests first:** `tests/unit/pacts/test_stack.py`,
`tests/unit/mills/test_stack.py`, repository integration extension.

**Files:** `pacts/stack.py`, `links/.../repositories.py` (`StackRepository`),
`mills/stack.py` (`StackService`) — enforcing at-most-one-stack-per-file.

---

### Step 15: TUI — stacks

**Files:** `gates/tui/textual/stacks.py` — create, list, add files, remove files,
show a stack's contents; `inits/services.py` gains the `stack` leaf.

---

### Step 16: TUI — filter files by stack

**Files:** `gates/tui/textual/files.py` — filter by stack. MVP complete.
