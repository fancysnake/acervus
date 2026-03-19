# Acervus

Filesystem tagging tool. Python 3.14, Poetry, mise.

## Commands

```bash
mise run start      # dev server :8000
mise run test       # all tests
mise run check      # format + lint
mise run dj <cmd>   # django-admin
```

## Architecture

GLIMPSE system:

- `gates` (views, forms, templatetags, clis)
- `links` (models, repos, external clients)
- `inits` (DI)
- `mills` (logic)
- `pacts` (protocols, DTOs, aggregates)
- `specs` (configuration options)
- `edges` (infrastructure boundary)

Access data: `request.di.uow.{repository}.read(id)` — returns Pydantic DTOs,
never Django models.

### Import rules

Enforced by `importlinter` in `pyproject.toml`.

Relation `X -> Y` means (Y can import X). Transitive and reflexive.

`pacts` -> `specs` -> `mills` -> `links` -> `gates` -> `inits`

| Layer | Cannot import |
|-------|---------------|
| pacts | gates, links, inits, mills, specs, edges, django |
| specs | gates, links, inits, mills, edges, django |
| mills | gates, links, inits, specs, edges, django |
| links | gates, inits, specs, edges |
| gates | links, inits, specs, edges |
| inits | edges |
| edges | gates, links, inits, mills, pacts, specs |

Edges are outside of the import system — not imported by any layer.

### Data flow

1. Request arrives, middleware in `inits` injects `request.di = DependencyInjector()`
2. View accesses `request.di.uow.{repo}.read(id)` — gets Pydantic DTO
3. Repository: check identity-map cache -> query ORM if miss -> cache -> return DTO
4. View passes DTOs to template

### pacts

Bottom layer. No imports from other project modules or Django.

- **DTOs**: Pydantic `BaseModel` with `ConfigDict(from_attributes=True)`.
  Fields mirror ORM model fields.
- **TypedDicts** (`total=False`): used for write/update operations.
- **Protocols**: interfaces for repositories, `UnitOfWorkProtocol`,
  `DependencyInjectorProtocol`.
- **Request types**: `RequestContext` / `AuthenticatedRequestContext` dataclasses,
  `RootRequestProtocol` with `.di` and `.context`.
- **Exceptions**: `NotFoundError` raised by repositories.

### mills

Pure business logic. Takes UoW/dependencies via constructor. No Django imports.

```python
class PanelService:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    def delete_category(self, category_pk: int) -> bool:
        if self._uow.categories.has_proposals(category_pk):
            return False
        self._uow.categories.delete(category_pk)
        return True
```

### links

Data access. Implements repository pattern with identity map.

**Storage** — request-scoped cache, simple `@dataclass` with dicts:

```python
@dataclass
class Storage:
    events: dict[int, Event] = field(default_factory=dict)
    users: dict[UserType, dict[str, User]] = field(
        default_factory=lambda: defaultdict(dict)
    )
```

**Repositories** — implement protocols from pacts, take Storage in `__init__`:

```python
class EventRepository(EventRepositoryProtocol):
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def read(self, pk: int) -> EventDTO:
        if not (event := self._storage.events.get(pk)):
            try:
                event = Event.objects.get(id=pk)
            except Event.DoesNotExist as exception:
                raise NotFoundError from exception
            self._storage.events[pk] = event
        return EventDTO.model_validate(event)
```

**Unit of Work** — owns Storage, exposes repositories as `@cached_property`:

```python
class UnitOfWork(UnitOfWorkProtocol):
    def __init__(self) -> None:
        self._storage = Storage()

    @staticmethod
    def atomic() -> AbstractContextManager[None]:
        return transaction.atomic()

    @cached_property
    def events(self) -> EventRepository:
        return EventRepository(self._storage)
```

### gates

Entry points. Receives DTOs from UoW, passes DTOs to templates.

```python
class EventIndexPageView(LoginRequiredMixin, TemplateView):
    template_name = "panel/event/index.html"

    def get(self, request: RootRequestProtocol, slug: str) -> TemplateResponse:
        event = request.di.uow.events.read_by_slug(slug, request.context.current_sphere_id)
        return TemplateResponse(request, self.template_name, {"event": event})
```

### inits

Wires dependencies. Middleware sets `request.di`:

```python
class DependencyInjector(DependencyInjectorProtocol):
    @cached_property
    def uow(self) -> UnitOfWork:
        return UnitOfWork()

class RepositoryInjectionMiddleware:
    def __call__(self, request: RootRequestProtocol) -> Response:
        request.di = DependencyInjector()
        return self.get_response(request)
```

### edges

Django infrastructure only: `settings.py`, `wsgi.py`, `asgi.py`.

## Source layout

```
src/{project}/
  pacts.py
  specs.py
  mills.py
  inits.py
  links/
    db/django/
      models.py
      admin.py
      migrations/
      storage.py
      repositories.py
      uow.py
    {service}.py          # external API clients
  gates/
    web/django/
      urls.py
      forms.py
      decorators.py
      context_processors.py
      templatetags/
      {namespace}.py      # view modules
    cli/django/
      management/commands/
  edges/
    settings.py
    wsgi.py
    asgi.py
  templates/
  static/
```

## URL conventions

### Pages (nouns, trailing slash)

- **url:** `/{namespace}/({subnamespace}/)?{page}/{subpage}/`
- **template:** `/{namespace}/({subnamespace}/)?{page}/{subpage}.html`
- **view:** `({Subnamespace})?{Page}{Subpage}PageView`

### Actions (verbs, `do` prefix, no trailing slash)

- **url:** `/{namespace}/({subnamespace}/)?({page}/{subpage}/)?do/{action}/{subaction}`
- **template:** none
- **view:** `({Subnamespace})?({Page}{Subpage})?{Action}ActionView`

### Components (nouns, `parts` prefix, no trailing slash)

- **url:** `/{namespace}/({subnamespace}/)?({page}/{subpage}/)?parts/{part}`
- **template:** `/{namespace}/({subnamespace}/)?({page}/{subpage}/)?parts/{part}.html`
- **view:** `({Subnamespace})?({Page}{Subpage})?{Part}ComponentView`

## Rules

- Views return DTOs to templates, never models
- Never touch `.env*` files
- NEVER modify, create, or delete configuration files without explicit
  per-case approval.
- NEVER add noqa/type ignore/pylint comments or directives without explicit
  per-case approval.
- When making UI changes, use agent-browser to take screenshots of affected
  pages and include before/after images in the PR description

## Testing

### Structure

```
tests/
  unit/                              # mirrors src/ structure
  integration/
    web/{namespace}/test_{url_name}.py
    cli/test_{command}.py
  e2e/                               # Playwright
  conftest.py
  integration/conftest.py
  integration/utils.py               # assert_response
```

### Unit tests (`tests/unit/`)

- Yes: classes, functions (mills, utilities)
- No: views, commands, repositories
- Write tests in classes
- Mock at the highest level to avoid side effects
- Check all mock calls
- No database access

Repositories are exempt from direct testing — implicitly tested through view
integration tests.

### Integration tests (`tests/integration/`)

- Yes: views, commands
- No: classes, functions
- Use pytest-factoryboy fixtures
- Mock at the lowest level or don't mock if possible
- Check all mock calls and side effects

Always use `assert_response`, never manual assertions:

```python
from http import HTTPStatus
from tests.integration.utils import assert_response

assert_response(
    response,
    HTTPStatus.OK,
    template_name=["namespace/page.html"],
    context_data={...},     # ALL keys, exact equality
    messages=[(messages.SUCCESS, "Saved.")],  # optional
)
```

- Use `ANY` only for hard-to-compare objects (forms, views), never for `[]`,
  `{}`, booleans, or simple values
- Login redirects: exact URL match (`url=f"/crowd/login-required/?next={url}"`)
- Magic numbers: use `1 + 1` pattern with comment (`== 1 + 1  # Email + Phone`)

### E2E tests (`tests/e2e/`)

- Full features, complete user flows

### TDD workflow

Plan -> Tests (red) -> Implement (green) -> Refactor.
Wait for approval between phases.

## Tooling

- **Black**: line-length 88, preview mode, Python 3.14 target
- **Ruff**: `select = ["ALL"]`, preview mode
- **MyPy**: strict mode, django-stubs plugin
- **Import Linter**: enforces GLIMPSE layer import rules
- **Djlint**: Django profile HTML linting
- **Codespell**: spell checking
- **Deptry**: dependency management
- **Coverage**: omit `edges/` and `migrations/`, target 100% common code
