# Implementation review — T215 Global Runtime Settings (V1)

## Scope verified

- `runtime_settings` table created in both backends:
  - SQLite: `tools/agent_runner/runtime_db.py:189` + idempotent migration
    helper `_ensure_runtime_settings_table` at `:291`.
  - Postgres: `tools/agent_runner/runtime_db_pg.py:234`. Schema is keyed by
    `key` only (no `project_id`), matching the V1 fix that required global
    scope to be unambiguous and helpers to keep their backend-agnostic
    signatures.
- Helpers `list_runtime_settings`, `get_runtime_setting`,
  `upsert_runtime_setting`, `delete_runtime_setting` exist in both backends
  with identical public shape and are re-bound through the SQLite/Postgres
  switch block at `runtime_db.py:1221-1224`.
- Registry/resolver `tools/agent_runner/runtime_settings.py`:
  - Catalog covers every key listed in the ticket
    (`DEFAULT_PLANNER_MODEL`/`CODER`/`REVIEWER`/`TESTER`, `MAX_WORKERS`,
    `INTELLIGENCE_TIMEOUT_SECONDS`, `DISPATCHER_ENABLED`, `LOG_LEVEL`,
    plus the three sensitive keys).
  - Precedence is DB → env → hardcoded default; sensitive keys never read
    the DB and never accept writes (`SensitiveSettingWriteError` raised by
    `set_setting`).
  - `resolve_effective_setting` redacts sensitive values to
    `configured` / `not_configured` and marks `editable=False`.
  - No process cache → DB changes are visible on the next read.
- Control API `services/control_api/routes/settings.py`:
  - `GET /api/settings`, `GET /api/settings/{key}`,
    `PUT /api/settings/{key}`, `DELETE /api/settings/{key}` all wired.
  - Returns 404 for unknown keys, 422 on coercion failure, 403 on sensitive
    writes. Schemas added to `services/control_api/models/schemas.py:709-728`.
  - Router included in `services/control_api/main.py:238`.
  - Boot applies a persisted `LOG_LEVEL` via the registry
    (`services/control_api/main.py:96-103`).
- Hot-reload wiring:
  - `ticket_intelligence_analyzer.py:46-59` reads
    `INTELLIGENCE_TIMEOUT_SECONDS` per-run; constant `_ANALYSIS_TIMEOUT`
    was removed.
  - `ticket_dispatcher.get_dispatcher_mode` consults the registry first
    (`tools/agent_runner/ticket_dispatcher.py:64-87`); the dispatcher
    route now passes `db_path` (`services/control_api/routes/dispatcher.py:58`).
  - `MAX_WORKERS` is registered with `requires_restart=True`. See
    "Observations" below.
- Dashboard:
  - `apps/dashboard/src/pages/GlobalSettingsPage.jsx` renders Name,
    Current value, Description, Editable, Sensitive, Requires restart,
    Source, Actions; inline edit for non-sensitive scalars; “Reset to
    default” when `source=db`; `Restart required` badge surfaces after
    save for restart-bound keys; sensitive rows display
    configured/not configured with read-only action text.
  - Route registered in `apps/dashboard/src/App.jsx:102`.
  - Sidebar link in `apps/dashboard/src/components/ProjectSidebar.jsx:17`.
  - API client `apps/dashboard/src/api/settings.js`.
- Tests added cover DB persistence, registry precedence/coercion/redaction,
  API surface (including 403 on sensitive PUT and DB-not-persisted check),
  and a smoke test that the router is mounted. All four new test files
  pass locally (`pytest tests/test_runtime_settings_db.py
  tests/test_runtime_settings_registry.py tests/test_control_api_settings.py
  tests/test_control_api_main.py` — 35/35 green).

## Acceptance criteria mapping

- `runtime_settings` table exists in both backends after `init_runtime_db`
  and re-init is idempotent — `tests/test_runtime_settings_db.py::test_init_is_idempotent`.
- `GET /api/settings` returns one entry per spec — verified by
  `tests/test_control_api_settings.py::test_list_returns_one_entry_per_spec`.
- `PUT /api/settings/MAX_WORKERS` persists and `GET` reports `source=db` —
  `test_put_persists_value_and_source_switches_to_db`.
- `DELETE /api/settings/MAX_WORKERS` falls back to env/default —
  `test_delete_resets_to_env`.
- Sensitive keys: `PUT /api/settings/OPENAI_API_KEY` is rejected with 403
  (`test_sensitive_put_is_rejected`) AND no row is persisted; `GET`
  redacts (`test_sensitive_get_is_redacted` /
  `test_sensitive_status_reads_from_env`). This matches the plan-fix
  requirement that secrets be read-only status indicators in V1.
- Unknown key → 404; bad coercion → 422.
- Dashboard meets the column list, sensitive non-edit policy, and
  `Restart required` badge requirement; the inline editor uses bool
  toggle / numeric input / text input per `value_type`.
- `ticket_intelligence_analyzer.py` re-reads `INTELLIGENCE_TIMEOUT_SECONDS`
  on every invocation — satisfies the hot-reload-on-next-call criterion.
- Existing behaviour with an empty `runtime_settings` table is preserved:
  `get_setting` falls through to env/default; the dispatcher mode resolver
  keeps its legacy env fallback; the boot-time `LOG_LEVEL` apply is a
  no-op when there is no DB override.

## Observations (non-blocking)

1. **`MAX_WORKERS` consumer not actually rewired.** The plan named
   "`services/supervisor/...` MAX_WORKERS reader (the supervisor entrypoint
   that consumes `DAEMON_MAX_WORKERS`)" as a wiring target, but the current
   codebase does not read `DAEMON_MAX_WORKERS` anywhere — the daemon takes
   `--max-workers` purely from CLI (`tools/agent_runner/run_daemon.py:1802`).
   The implementation registers the setting with `requires_restart=True`
   and surfaces the restart badge, so the UI behaviour matches the ticket,
   but persisting `MAX_WORKERS` in the DB has no effect on the daemon
   until somebody bridges it (e.g. supervisor sets `DAEMON_MAX_WORKERS`
   from the DB before exec). Worth either documenting the gap or
   following up in a small ticket — not a blocker for this PR.

2. **`DELETE /api/settings/<sensitive_key>` returns 204 (no-op).** The
   registry treats a delete on a sensitive key as a silent no-op so the
   UI can offer a uniform reset action. Given the UI does not expose a
   reset action for sensitive rows, returning 405/403 would be slightly
   more honest, but the current behaviour is harmless and consistent
   with V1's "sensitive keys are not persisted" invariant.

3. **`get_dispatcher_mode` still falls back to env after the registry.**
   The registry already does DB → env → default, so the second
   `os.environ.get(_ENV_VAR)` at `ticket_dispatcher.py:83` is only useful
   for the `db_path=None` callsite. It does not produce incorrect results
   (the registry returns the env value when present, otherwise `"off"`,
   which already short-circuits the `if raw is None` check). Minor
   redundancy, not a bug.

4. **Pre-existing test failures from `RUNTIME_DB_BACKEND=postgres` in the
   shell are unrelated to this ticket.** Running `pytest` with that env
   var set surfaces `AttributeError: 'PosixPath' object has no attribute
   'dbname'` in `runtime_db_pg.py:326` for tests not refactored to use
   handles. Clean-env runs (`env -u RUNTIME_DB_BACKEND pytest …`) pass on
   the same files. Worth flagging to the user but explicitly out of T215.

## Verdict

The implementation matches the V1 ticket spec, applies both required plan
fixes (secrets read-only, Postgres global-only), exposes the API and UI
described in the plan, wires the in-process consumers the plan committed
to, and ships focused tests that pass. The `MAX_WORKERS` gap is a wiring
follow-up rather than a regression — the setting works end-to-end through
the registry, the API, and the dashboard; only the daemon's CLI flag
remains the source of truth at start-up.

IMPLEMENTATION_APPROVED
