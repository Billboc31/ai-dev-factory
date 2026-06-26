## Summary

Implemented T216 strictly per the approved plan. The empty `runtime_settings` table is now an observable, supported steady state — and any future regression that swallows the full list will surface in logs / as a 500 instead of producing an empty page.

### Files modified
- **`services/control_api/routes/settings.py`** — Added invariant docstring on `list_settings` (always returns `len(SETTING_SPECS)` entries). Wrapped `list_effective_settings(db)` in `try/except Exception` that logs via `logger.exception(...)` and re-raises as HTTP 500 instead of returning `{"settings": []}` silently.
- **`tools/agent_runner/runtime_settings.py`** — Added a module-level `logger` and a `_warned_db_failures: set[str]` registry. The existing per-key `except Exception` in `resolve_effective_setting` now logs a single warning the first time a key's DB read fails (behaviour — fall back to env/default — is unchanged).
- **`tests/test_control_api_settings.py`** — Added the 5 tests from the plan:
  1. `test_list_returns_all_settings_on_empty_table`
  2. `test_list_source_is_default_when_no_env_no_db`
  3. `test_list_source_is_env_when_no_db`
  4. `test_list_source_switches_to_db_after_put`
  5. `test_list_survives_missing_runtime_settings_table` (DROPs the table, then GETs)

  Plus a small helper `_clear_all_spec_env_vars(monkeypatch)` that unsets every `env_var` declared in `SETTING_SPECS` so the tests don't pick up values leaked from the host env.

### Verifications
- `pytest tests/test_control_api_settings.py tests/test_runtime_settings_registry.py tests/test_runtime_settings_db.py` → **35 passed** (10 pre-existing API + 5 new + 12 registry + 8 db).

### Limits / hypotheses
- The empty-table contract is verified at the API level (TestClient against SQLite). I did not perform the manual `docker-compose up` browser check listed in the acceptance criteria — that requires a runtime I can't exercise here. The empty-state branch in `GlobalSettingsPage.jsx:250` was intentionally left as a defensive guard per the plan.
- The warn-once registry is process-local and not reset between calls — that's the intended behaviour ("first occurrence per key"). Test isolation isn't affected because each test creates a fresh DB and the resolver code path is unchanged on the happy path.
