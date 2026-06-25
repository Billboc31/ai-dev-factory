## Objective

Introduce V1 of a global Runtime Settings layer: persist a small set of
administrator-tunable values in the runtime database, expose them through a
`/api/settings` REST surface, render them on a new `Global Settings`
dashboard page, and route in-process reads through a single registry so that
DB overrides take precedence over `.env` and hardcoded defaults with
hot-reload semantics for the keys that can safely be re-read on the fly.

## Included

### 1. Runtime DB schema — `runtime_settings` table

- `tools/agent_runner/runtime_db.py`
  - Add `runtime_settings` block to the `_SCHEMA` constant. Columns (SQLite):
    `key TEXT PRIMARY KEY`, `value TEXT NOT NULL`, `value_type TEXT NOT NULL`
    (one of `string|int|float|bool|secret`), `scope TEXT NOT NULL DEFAULT
    'global'`, `description TEXT`, `is_sensitive INTEGER NOT NULL DEFAULT 0`,
    `requires_restart INTEGER NOT NULL DEFAULT 0`, `updated_at TEXT NOT NULL`,
    `updated_by TEXT`.
  - Add an idempotent migration helper `_ensure_runtime_settings_table(conn)`
    called from `init_runtime_db()` so existing SQLite files gain the table
    without quarantine.
  - Add helpers: `list_runtime_settings(db_path) -> list[dict]`,
    `get_runtime_setting(db_path, key) -> dict | None`,
    `upsert_runtime_setting(db_path, key, *, value, value_type, scope='global',
    description=None, is_sensitive=False, requires_restart=False,
    updated_by=None)`, `delete_runtime_setting(db_path, key)`.

- `tools/agent_runner/runtime_db_pg.py`
  - Mirror schema in `_DDL` with composite key `(project_id, key)` and `scope
    TEXT NOT NULL DEFAULT 'global'` (V1 only writes/reads `scope='global'`;
    `project_id` carries the per-project scoping that Postgres already does
    for every other table).
  - Mirror the four helpers above with the same public names.
  - Rebind them in the `_RUNTIME_DB_BACKEND == "postgres"` switch block at
    the bottom of `runtime_db.py`.

### 2. Settings registry and resolver (Python)

- New module `tools/agent_runner/runtime_settings.py`:
  - Declare `SETTING_SPECS: dict[str, SettingSpec]` for the V1 keys:
    `DEFAULT_PLANNER_MODEL`, `DEFAULT_CODER_MODEL`,
    `DEFAULT_REVIEWER_MODEL`, `DEFAULT_TESTER_MODEL`, `MAX_WORKERS`,
    `INTELLIGENCE_TIMEOUT_SECONDS`, `DISPATCHER_ENABLED`, `LOG_LEVEL`,
    `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`.
  - Each `SettingSpec` carries: `key`, `value_type`, `description`,
    `is_sensitive`, `requires_restart`, `default` (hardcoded fallback),
    `env_var` (the existing `.env` key it maps to — e.g. `MAX_WORKERS` →
    `DAEMON_MAX_WORKERS`, `INTELLIGENCE_TIMEOUT_SECONDS` →
    `AI_DEV_FACTORY_INTEL_TIMEOUT`, `DISPATCHER_ENABLED` →
    `TICKET_DISPATCHER_MODE`), and an optional `coerce` callable.
  - Public API:
    - `get_setting(db_path, key) -> Any` — reads DB first, then `os.environ`
      (via `env_var`), then `default`. Coerces to `value_type`. Never
      returns a `secret` value to non-trusted callers (sensitive flag is
      enforced at the API layer, not here; this function returns the raw
      value for in-process use).
    - `resolve_effective_setting(db_path, key) -> dict` — returns
      `{key, value, value_type, source: 'db'|'env'|'default', is_sensitive,
       requires_restart, description, updated_at, updated_by}`.
      For `is_sensitive=True`, replaces `value` with the string
      `"configured"` or `"not_configured"` (never the raw secret).
    - `list_effective_settings(db_path) -> list[dict]` — iterates
      `SETTING_SPECS` and calls `resolve_effective_setting`.
    - `set_setting(db_path, key, value, *, updated_by=None) -> dict` —
      validates and coerces against the spec, calls
      `runtime_db.upsert_runtime_setting`, returns the new effective row.
    - `delete_setting(db_path, key) -> None` — removes the DB override so
      the layer falls back to `.env`/default.

- Re-read semantics: `get_setting` always re-queries the DB. No process-level
  cache in V1 — that is the cheapest correct way to deliver "change MAX_WORKERS
  → new value immediately available" without inventing an invalidation bus.
  Tight inner loops are not in scope.

### 3. Wire the resolver into the candidate consumption sites

For each candidate setting, replace the existing direct `os.environ.get(...)`
read with `runtime_settings.get_setting(db, KEY)` so DB overrides actually take
effect at runtime. V1 wires only the call sites already identified:

- `tools/agent_runner/ticket_intelligence_analyzer.py` — replace the
  module-level constant `_ANALYSIS_TIMEOUT = int(os.environ.get(
  "AI_DEV_FACTORY_INTEL_TIMEOUT", "120"))` with a function-scoped call to
  `runtime_settings.get_setting(db, "INTELLIGENCE_TIMEOUT_SECONDS")` at the
  point the timeout is used (so it is hot-reloaded).
- `tools/agent_runner/ticket_dispatcher.py` — change `get_dispatcher_mode()`
  to call `runtime_settings.get_setting(db, "DISPATCHER_ENABLED")` (still
  honouring the existing env var via the registry’s `env_var` fallback).
- `services/supervisor/...` MAX_WORKERS reader (the supervisor entrypoint
  that consumes `DAEMON_MAX_WORKERS`) — route through `get_setting`.
- `services/control_api/main.py` boot logging — call
  `logging.getLogger().setLevel(get_setting(db, "LOG_LEVEL"))` after
  `init_runtime_db`. `LOG_LEVEL` is hot-reload safe (logging level is
  global mutable state); model-name settings are also safe.
  Keys marked `requires_restart=True` in V1: none of the core models
  (treat them as hot). `MAX_WORKERS` is `requires_restart=True` because
  the daemon pool size is read at start; the API still accepts the write,
  and the UI shows a `Restart required` badge.

Do not touch the call sites of secret keys (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`) in V1 — they are exposed read-only
through the registry but their consumers continue reading `os.environ`
directly. The API allows writing them (which updates the DB row) and the
UI shows `configured` / `not configured`; full secret rotation is out of
scope.

### 4. Control API endpoints

- New module `services/control_api/routes/settings.py`:
  - `GET /api/settings` → `RuntimeSettingsListResponse` — calls
    `runtime_settings.list_effective_settings(db)`. Sensitive entries are
    redacted (`value="configured"|"not_configured"`).
  - `GET /api/settings/{key}` → `RuntimeSetting` — 404 if `key` is not in
    `SETTING_SPECS`; otherwise returns the effective row (redacted if
    sensitive).
  - `PUT /api/settings/{key}` with body `RuntimeSettingUpdate
    {value: str, updated_by: str | None}`. Validates `key` against
    `SETTING_SPECS`, coerces `value` to `value_type`, persists via
    `runtime_settings.set_setting`. Returns the new effective row
    (redacted for sensitive). Returns 422 on coercion failure, 404 on
    unknown key.
  - `DELETE /api/settings/{key}` → 204; resets the override.
- Add new Pydantic schemas to `services/control_api/models/schemas.py`:
  `RuntimeSetting`, `RuntimeSettingsListResponse`, `RuntimeSettingUpdate`.
- Wire the router into `services/control_api/main.py` (import + a single
  `app.include_router(settings.router)` line under the existing block).
- Routes use `request.app.state.db_path`, mirroring the rules / dispatcher
  routes pattern.

### 5. Dashboard UI — Global Settings page

- New API client `apps/dashboard/src/api/settings.js` with
  `listSettings()`, `getSetting(key)`, `updateSetting(key, value)`,
  `resetSetting(key)`.
- New page `apps/dashboard/src/pages/GlobalSettingsPage.jsx`:
  - Table with columns: Name, Current value, Description, Editable,
    Sensitive, Requires restart, Source (`db` / `env` / `default`).
  - Inline edit (text input for `string` / `int` / `float`, toggle for
    `bool`). On save, calls `PUT /api/settings/{key}` and refreshes.
  - Sensitive rows: display `configured` / `not configured`; edit
    control is a single masked input that only sends a value when the
    user clicks save. Never render the existing value.
  - `requires_restart=true` rows show a `Restart required` badge after
    edit until the page is reloaded after a backend restart.
  - A `Reset to default` action per row issues `DELETE
    /api/settings/{key}`.
- Register the route in `apps/dashboard/src/App.jsx`:
  `<Route path="/settings" element={<GlobalSettingsPage />} />`.
- Add a `Global Settings` link in
  `apps/dashboard/src/components/ProjectSidebar.jsx` (sits in the
  global, not project-scoped, section).

### 6. Tests

- `tests/test_runtime_settings_db.py` — direct DB helpers:
  table creation idempotency, upsert/get/list/delete, sensitive flag
  round-trip, requires_restart round-trip.
- `tests/test_runtime_settings_registry.py` — `get_setting` precedence
  (DB > env > default), coercion (`int`/`float`/`bool`),
  `resolve_effective_setting` source attribution, sensitive redaction.
- `tests/test_control_api_settings.py` — FastAPI TestClient:
  `GET /api/settings`, `GET /api/settings/{key}`, `PUT /api/settings/{key}`
  for non-sensitive and sensitive keys (verifies redaction on read),
  `DELETE /api/settings/{key}` falls back to env, 404 on unknown key,
  422 on bad coercion.
- One smoke test (`tests/test_control_api_main.py` is the existing host):
  asserts the new router is registered (`/api/settings` returns 200).

## Excluded

- Project-scoped settings (`scope != 'global'`). V1 writes/reads only
  `scope='global'`; the column exists for forward compatibility.
- Replacing all existing `.env` reads. Only the call sites listed in
  section 3 are rewired in this ticket.
- Automatic process restart when `requires_restart=true` settings change.
  The UI surfaces the badge; the operator restarts manually.
- Secret encryption at rest, rotation, or audit log.
  `is_sensitive` only controls UI redaction; the DB stores the value in
  plain text.
- Dispatcher / scheduler / Traefik configuration redesign.
- Caching layer or invalidation bus for the registry.
- Authentication / RBAC on the new endpoints (the existing control API
  has none; adding it is a separate ticket).
- Migration of historical `.env.example` defaults into the DB on
  bootstrap. The system continues to work with an empty
  `runtime_settings` table.

## Acceptance criteria

- `runtime_settings` table exists in both backends after
  `init_runtime_db()`; re-running init does not duplicate columns or rows.
- `GET /api/settings` returns one entry per key in `SETTING_SPECS` with
  `source` correctly set to `db`, `env`, or `default`.
- `PUT /api/settings/MAX_WORKERS` with body `{"value": "5"}` persists the
  value, and a subsequent `GET` returns `source: "db"` and `value: "5"`.
- `DELETE /api/settings/MAX_WORKERS` removes the override; the next
  `GET` returns the value from `os.environ["DAEMON_MAX_WORKERS"]` (or
  the hardcoded default) with `source` set to `env` or `default`.
- `PUT /api/settings/OPENAI_API_KEY` accepts a value; `GET` returns
  `value: "configured"` and never the raw secret. The same holds for
  `ANTHROPIC_API_KEY` and `GITHUB_TOKEN`.
- `PUT /api/settings/UNKNOWN_KEY` returns 404. `PUT
  /api/settings/MAX_WORKERS` with body `{"value": "not-an-int"}` returns
  422.
- The dashboard `/settings` route renders the table with the columns
  listed in section 5, allows inline edit for non-sensitive keys,
  surfaces `Restart required` for `MAX_WORKERS`, and never displays
  existing secret values.
- `ticket_intelligence_analyzer.py` honours a DB override of
  `INTELLIGENCE_TIMEOUT_SECONDS` on the next invocation, without a
  process restart.
- All existing tests pass; the new test files listed in section 6 pass.
- When the `runtime_settings` table is empty, every existing call site
  still resolves the same value it resolved before this ticket (env or
  hardcoded default).
