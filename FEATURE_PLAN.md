# Acervus MVP Plan

## Context

Acervus is a CLI file-tagging tool (like TMSU). Organizes files via marks (labels) and stacks (groups). SQLite database, TOML config, paths relative to named roots. CLI command: `acre`.

**Naming:** acervus (project), acre (CLI), mark (label), stack (file group).

Architecture: GLIMPSE layering, SQLAlchemy + SQLite, Click CLI.

## Import Rules (from pyproject.toml)

| Layer | CAN import | CANNOT import |
|-------|-----------|---------------|
| pacts | nothing | gates, links, inits, mills, specs, edges |
| specs | pacts | gates, links, inits, mills, edges |
| mills | pacts | gates, links, inits, specs, edges |
| links | pacts, mills | gates, inits, specs, edges |
| gates | pacts, mills | links, inits, specs, edges |
| inits | pacts, specs, mills, links, gates | edges |
| edges | nothing | gates, links, inits, mills, pacts, specs |

**Key constraint:** Only `inits` can wire specs, links, and gates together. Gates and mills cannot import links or specs directly.

## Architecture Decisions

### Entry point: `inits` wraps `gates`

```
pyproject.toml: acre = "acervus.inits:cli"

inits/__init__.py:
  - imports cli group from gates.cli.commands
  - adds Click callback that loads config (specs) and creates DI (links UoW)
  - injects DI container via ctx.obj

gates/cli/commands.py:
  - defines Click commands
  - accesses ctx.obj for DI (no imports from links/specs/inits)
  - can import mills (allowed) and pacts (allowed) for type hints
```

### Config: model in specs, loading in inits

- `specs/__init__.py`: `AcervusConfig` Pydantic model (pure definition)
- `inits/__init__.py`: `load_config()` reads TOML via `tomllib`, returns `AcervusConfig`

### Filesystem I/O: protocol in pacts, implementation in links

- `pacts/__init__.py`: `FilesystemReaderProtocol`, `FileInfo` dataclass
- `links/filesystem.py`: `FilesystemReader` implements the protocol
- `mills/__init__.py`: `ScanService` receives reader via constructor (no I/O)

### File paths: use existing packages

All layers are already packages (`__init__.py` dirs). New files go inside them:
- `pacts/__init__.py`, `specs/__init__.py`, `mills/__init__.py`, `inits/__init__.py`
- `links/db/models.py`, `links/db/engine.py`, `links/db/repositories.py`, `links/db/uow.py`
- `links/filesystem.py`
- `gates/cli/commands.py` (exists)

## Steps

Each step follows TDD: write tests (red) -> implement (green) -> verify with `mise run check` + `mise run test`.

---

### Step 0: Entry point adjustment

**Change:** `pyproject.toml` entry point from `acervus.gates.cli.commands:cli` to `acervus.inits:cli`

**Files:**
- `pyproject.toml` — change `[project.scripts]`
- `src/acervus/inits/__init__.py` — import and re-export `cli` from gates (no callback yet)

**Verify:** `poetry run acre --help` works, `mise run check` passes

---

### Step 1: pacts — DTOs, protocols, exceptions

**Tests first:** `tests/unit/pacts/test_dtos.py` — DTO validation, `from_attributes=True`

**Files:** `src/acervus/pacts/__init__.py`

- DTOs: `RootDTO`, `FileDTO`, `MarkDTO`, `StackDTO` (Pydantic `BaseModel`, `ConfigDict(from_attributes=True)`)
- Dataclasses: `FileInfo` (relative_path, size, mtime), `ScanResult` (added, removed, updated)
- Protocols: `FilesystemReaderProtocol`, `RootRepositoryProtocol`, `FileRepositoryProtocol`, `MarkRepositoryProtocol`, `StackRepositoryProtocol`, `UnitOfWorkProtocol`, `DependencyInjectorProtocol`
- Exceptions: `NotFoundError`

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 2: specs — Configuration model

**Tests first:** `tests/unit/specs/test_config.py` — config validation

**Files:** `src/acervus/specs/__init__.py`

- `AcervusConfig(BaseModel)`: `db_path: Path`, `roots: dict[str, Path]`

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 3: inits — Config loading + DI bootstrap

**Tests first:** `tests/unit/inits/test_config_loading.py` — load from temp TOML file

**Files:** `src/acervus/inits/__init__.py`

- `load_config(path: Path | None = None) -> AcervusConfig` — uses `tomllib`, default `~/.config/acervus/config.toml`
- `DependencyInjector` — stub, takes config
- Click callback on the `cli` group: loads config, creates DI, stores on `ctx.obj`

**Verify:** `poetry run acre --help` works, `mise run check` passes, `mise run test` passes

---

### Step 4: `acre status` command

**Tests first:** `tests/integration/cli/test_status.py` — with temp config, assert output

**Files:** `src/acervus/gates/cli/commands.py`

- `status` subcommand: reads config from `ctx.obj`, prints roots + db path
- gates imports only `click` and `pacts` (for protocol types if needed)

**Verify:** `poetry run acre status` prints config, `mise run check` passes, `mise run test` passes

---

### Step 5: links — SQLAlchemy models + engine

**Files:**
- `src/acervus/links/db/__init__.py` (new dir)
- `src/acervus/links/db/models.py` — `Root`, `File`, `Mark`, `FileMark`, `Stack`
- `src/acervus/links/db/engine.py` — `create_engine_from_path(db_path: Path) -> Engine`, `init_db(engine)`

**Verify:** `mise run check` passes

---

### Step 6: links — UoW + RootRepository

**Tests first:** `tests/unit/links/test_uow.py` — session lifecycle with in-memory SQLite

**Files:**
- `src/acervus/links/db/uow.py` — implements `UnitOfWorkProtocol`
- `src/acervus/links/db/repositories.py` — `RootRepository` with `sync_roots()`, `list_all()`, `read()`, `read_by_alias()`

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 7: Wire DI with real UoW + update status

**Files:** `src/acervus/inits/__init__.py`

- `DependencyInjector`: creates engine, calls `init_db`, exposes `uow` property
- Update `acre status` output: show "Database: path (exists/new)", root count, file count

**Integration test:** `tests/integration/cli/test_status.py` — verify DB creation and status output

**Verify:** `poetry run acre status` works end-to-end, `mise run check` passes, `mise run test` passes

---

### Step 8: links — FilesystemReader

**Tests first:** `tests/unit/links/test_filesystem.py` — temp dir with files

**Files:** `src/acervus/links/filesystem.py` — implements `FilesystemReaderProtocol`

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 9: mills — ScanService (basic insert)

**Tests first:** `tests/unit/mills/test_scan.py` — mock UoW + FS reader

**Files:**
- `src/acervus/mills/__init__.py` — `ScanService(uow, fs)` with `scan(alias, root_path) -> ScanResult`
- `src/acervus/links/db/repositories.py` — add `FileRepository` basics

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 10: `acre scan` command

**Tests first:** `tests/integration/cli/test_scan.py` — temp dir, scan, verify output

**Files:**
- `src/acervus/gates/cli/commands.py` — `scan [ALIAS]` command, uses `ctx.obj` DI
- `src/acervus/inits/__init__.py` — wire `FilesystemReader` + `ScanService` into DI

**Verify:** `poetry run acre scan` works, `mise run check` passes, `mise run test` passes

---

### Step 11: mills — ScanService full diff

**Tests first:** `tests/unit/mills/test_scan.py` — added/removed/updated scenarios

**Files:** `src/acervus/mills/__init__.py` — extend scan to detect removals and modifications

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 12: `acre files` command

**Tests first:** `tests/integration/cli/test_files.py`

**Files:**
- `src/acervus/links/db/repositories.py` — `FileRepository.list_all()`, `list_by_root()`
- `src/acervus/gates/cli/commands.py` — `files [--root ALIAS]`, output: `alias:relative/path`

**Verify:** Works end-to-end, `mise run check` passes, `mise run test` passes

---

### Step 13: mills — MarkService + MarkRepository

**Tests first:** `tests/unit/mills/test_mark.py` — mock UoW

**Files:**
- `src/acervus/mills/__init__.py` — `MarkService(uow)` with `add()`, `remove()`
- `src/acervus/links/db/repositories.py` — `MarkRepository`

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 14: `acre mark` commands

**Tests first:** `tests/integration/cli/test_mark.py`

**Files:** `src/acervus/gates/cli/commands.py`

- `acre mark add <file> <mark> [<mark>...]`
- `acre mark remove <file> <mark> [<mark>...]`
- `acre mark list` — all marks with file counts
- `acre marks <file>` — marks for a specific file

**Verify:** Full mark workflow, `mise run check` passes, `mise run test` passes

---

### Step 15: `acre files` — mark filtering

**Tests first:** extend `tests/integration/cli/test_files.py`

**Files:** `src/acervus/gates/cli/commands.py` — add `--mark MARK`, `--unmarked` flags

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 16: mills — StackService + StackRepository

**Tests first:** `tests/unit/mills/test_stack.py`

**Files:**
- `src/acervus/mills/__init__.py` — `StackService(uow)`
- `src/acervus/links/db/repositories.py` — `StackRepository`

**Verify:** `mise run check` passes, `mise run test` passes

---

### Step 17: `acre stack` commands

**Tests first:** `tests/integration/cli/test_stack.py`

**Files:** `src/acervus/gates/cli/commands.py`

- `acre stack create <name>`
- `acre stack list`
- `acre stack add <stack> <file> [<file>...]`
- `acre stack remove <file> [<file>...]`
- `acre stack show <name>`

**Verify:** Full stack workflow, `mise run check` passes, `mise run test` passes

---

### Step 18: `acre files --stack` filtering

**Tests first:** extend `tests/integration/cli/test_files.py`

**Files:** `src/acervus/gates/cli/commands.py` — add `--stack STACK` flag

**Verify:** All tests pass, all checks pass. MVP complete.

---

## Key Files

| Layer | Files |
|-------|-------|
| pacts | `src/acervus/pacts/__init__.py` |
| specs | `src/acervus/specs/__init__.py` |
| mills | `src/acervus/mills/__init__.py` |
| links | `src/acervus/links/db/{__init__,models,engine,repositories,uow}.py`, `src/acervus/links/filesystem.py` |
| gates | `src/acervus/gates/cli/{__init__,commands}.py` |
| inits | `src/acervus/inits/__init__.py` |
| tests | `tests/unit/{pacts,specs,inits,mills,links}/`, `tests/integration/cli/` |
