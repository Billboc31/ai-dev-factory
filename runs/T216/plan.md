## Objective
Guarantee that `GET /api/settings` always returns one entry per `SETTING_SPECS` key — with values resolved by `DB override > env > default` — even when the `runtime_settings` table is empty or absent. Add regression tests that lock the empty-table contract so the dashboard is never blank on a fresh install.

## Included
- Reproduction (no code change yet):
  - Run `pytest tests/test_control_api_settings.py::test_list_returns_one_entry_per_spec`. It currently exercises an empty DB via `_make_app(tmp_path)` and is expected to pass against the current resolver.
  - Add a temporary local repro that mirrors a fresh install: stand up the FastAPI app with an isolated DB containing zero rows in `runtime_settings`, hit `GET /api/settings`, and confirm the response. If the response is empty in any path, capture the exception in `services/control_api/routes/settings.py::list_settings` (currently silent) and identify the failing call site.
- Code change in `services/control_api/routes/settings.py` (lines 53–58):
  - Wrap the call to `_runtime_settings.list_effective_settings(db)` in a single `try/except Exception` that logs the failure via `logger.exception(...)` and re-raises as a 500. This makes any future "empty list" regression visible in logs instead of silently returning `{"settings": []}`.
  - Add a short module-level docstring/comment on `list_settings` stating the invariant: "always returns `len(SETTING_SPECS)` entries; never DB-filtered".
- Code change in `tools/agent_runner/runtime_settings.py` (lines 260–306, `resolve_effective_setting`):
  - Narrow the existing `except Exception` around `runtime_db.get_runtime_setting` to log a warning on the first occurrence per key (use a module-level `_warned: set[str]`) so a missing/broken table is observable without flooding logs. Behaviour (fall back to env/default) stays identical.
  - No change to `list_effective_settings(db_path)` (already iterates `SETTING_SPECS`).
- Tests added to `tests/test_control_api_settings.py`:
  1. `test_list_returns_all_settings_on_empty_table(tmp_path)`: after `_make_app(tmp_path)` (DB initialised, zero rows), assert the response contains exactly `set(SETTING_SPECS.keys())`, has length `len(SETTING_SPECS)`, and every non-sensitive row reports `source in {"env", "default"}`.
  2. `test_list_source_is_default_when_no_env_no_db(tmp_path, monkeypatch)`: unset every `env_var` declared in `SETTING_SPECS`, hit `GET /api/settings`, assert every non-sensitive entry reports `source == "default"` and `value == spec.default`.
  3. `test_list_source_is_env_when_no_db(tmp_path, monkeypatch)`: set `DAEMON_MAX_WORKERS=4` (and one other non-sensitive env_var), hit `GET /api/settings`, assert those two rows have `source == "env"` with coerced values, and the rest fall through to `default`.
  4. `test_list_source_switches_to_db_after_put(tmp_path)`: PUT one key, GET the full list, assert that key has `source == "db"` with the new value, and the other entries are unaffected and still have `source in {"env", "default"}`.
  5. `test_list_survives_missing_runtime_settings_table(tmp_path)`: open the SQLite file, `DROP TABLE runtime_settings`, then GET — assert the endpoint returns 200 with all `SETTING_SPECS` keys and `source in {"env", "default"}`.
- No changes to:
  - `services/control_api/models/schemas.py` (`RuntimeSetting`, `RuntimeSettingsListResponse`).
  - `apps/dashboard/src/pages/GlobalSettingsPage.jsx` (existing empty-state branch stays as a defensive guard).
  - `tools/agent_runner/runtime_db.py` / `runtime_db_pg.py` (no schema or query changes).

## Excluded
- Encryption-at-rest or any change to how sensitive keys are read (still env-only, never persisted).
- Project-scoped settings (`scope` stays global in V1).
- New `SETTING_SPECS` entries, renamed keys, or coercion changes.
- Frontend cosmetic changes (badges, banner copy, empty-state messaging).
- Caching, hot-reload triggers, or invalidation buses.
- Backfilling default rows into `runtime_settings` at boot (resolution must remain stateless — the empty-table case is the supported steady state on fresh installs).

## Acceptance criteria
- `GET /api/settings` returns exactly `len(SETTING_SPECS)` entries when `runtime_settings` is empty, with each row's `source` ∈ `{"db", "env", "default"}`.
- `GET /api/settings` still returns all entries when the `runtime_settings` table is dropped (resolves via `env`/`default`); the failure is logged via `logger.exception` rather than swallowed silently.
- After `PUT /api/settings/<key>` with a non-sensitive key, the subsequent `GET /api/settings` shows that key with `source == "db"` and the new value; all other keys remain at `source` ∈ `{"env", "default"}`.
- Sensitive keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`) appear in the list with `value` ∈ `{"configured", "not_configured"}`, `editable == False`, and `source` ∈ `{"env", "default"}`.
- All five new tests pass; `test_list_returns_one_entry_per_spec` and every other test in `tests/test_control_api_settings.py`, `tests/test_runtime_settings_registry.py`, `tests/test_runtime_settings_db.py` still pass.
- On a fresh install, opening `/settings` in the dashboard shows a populated table (verified manually with `docker-compose up` against an empty DB; the `No settings declared.` row from `GlobalSettingsPage.jsx:250` is not rendered).
