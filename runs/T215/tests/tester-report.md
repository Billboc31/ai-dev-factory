# T215 — Tester Report

Branch: `ticket/T215-add-global-runtime-settings-page-backed-by-databas`
State on entry: `IMPLEMENTATION_APPROVED`
Verdict: **PASS**

## Commands executed

```text
RUNTIME_DB_BACKEND=sqlite \
  python -m pytest tests/test_runtime_settings_db.py \
                   tests/test_runtime_settings_registry.py \
                   tests/test_control_api_settings.py \
                   tests/test_control_api_main.py -v
# → 35 passed

RUNTIME_DB_BACKEND=sqlite \
  python -m pytest tests/test_ticket_dispatcher.py \
                   tests/test_ticket_dispatcher_api.py \
                   tests/test_control_api_main.py -v
# → 25 passed (validates T215-touched call sites)

RUNTIME_DB_BACKEND=sqlite python -m pytest tests/ \
  --ignore=tests/test_runtime_settings_db.py \
  --ignore=tests/test_runtime_settings_registry.py \
  --ignore=tests/test_control_api_settings.py -q
# → 115 failed, 1787 passed (T215 branch)

# Regression baseline — same command on main (detached worktree)
# → 115 failed, 1786 passed (main)

diff <(sort branch_failures) <(sort main_failures)
# → identical
```

The +1 extra passing test on T215 vs. main is
`tests/test_control_api_main.py::test_settings_router_is_registered`,
which is new in this branch.

## Regression analysis

The 115 pre-existing failures (mostly `test_control_api_artifacts.py`,
`test_control_api_endpoints.py`, `test_sandbox_worktree.py`,
`test_ticket_timeline.py`, `test_traefik_separation.py`) reproduce
identically on `main` at HEAD `16dd0dc6`. They are environmental
(tests read the worktree's real `runs/` directory, or expect a git
remote, or assume Traefik fixtures) — **not** regressions caused by
T215. The implementation review's note of "9 failures pre-existing on
main" was understated; the actual baseline is 115. Either way, the
failure sets on `main` and `T215` are bit-for-bit identical: zero new
failures.

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | A new Global Settings page exists in the dashboard | PASS | `apps/dashboard/src/pages/GlobalSettingsPage.jsx`, route mounted in `App.jsx:102`, sidebar link in `ProjectSidebar.jsx:17` |
| 2 | Runtime settings are persisted in the database | PASS | `runtime_settings` table created in both SQLite (`runtime_db.py:189-197` + idempotent migration `_ensure_runtime_settings_table`) and Postgres (`runtime_db_pg.py:234-242`); `test_schema_creates_runtime_settings`, `test_upsert_and_get_round_trip`, `test_init_is_idempotent` all pass |
| 3 | Runtime settings override `.env` values when present | PASS | `runtime_settings.get_setting` consults DB first, then env (`runtime_settings.py:219-249`); `test_get_setting_db_overrides_env` passes; API integration `test_put_persists_value_and_source_switches_to_db` passes |
| 4 | Non-sensitive settings can be edited from the UI | PASS | `GlobalSettingsPage` renders inline editors for `string`/`int`/`float`/`bool`; `PUT /api/settings/{key}` integration tests pass (`test_put_persists_value_and_source_switches_to_db`, `test_set_setting_coerces_to_value_type`) |
| 5 | Sensitive settings are never displayed in plain text | PASS | Registry returns `configured`/`not_configured` only for `is_sensitive=True` (`runtime_settings.py:276-280`); `test_resolve_sensitive_redacts_value`, `test_sensitive_get_is_redacted`, `test_sensitive_status_reads_from_env` pass; UI maps the redacted value verbatim (`GlobalSettingsPage.jsx:16-18`) |
| 6 | The UI indicates whether a setting requires restart | PASS | "Requires restart" column + amber "Restart required" badge surfaced after save (`GlobalSettingsPage.jsx:200-212`); `MAX_WORKERS` spec carries `requires_restart=True` (`runtime_settings.py:131`) |
| 7 | Hot reload works for supported settings | PASS | `runtime_settings.get_setting` re-queries the DB on every call (no in-process cache); `ticket_intelligence_analyzer.py:457-475` re-reads `INTELLIGENCE_TIMEOUT_SECONDS` per `run_analysis`; `ticket_dispatcher.get_dispatcher_mode(db_path)` re-reads `DISPATCHER_ENABLED`; `services/control_api/main.py:92-101` applies `LOG_LEVEL` on startup via the registry |
| 8 | Existing behavior continues to work when no DB setting exists | PASS | `test_get_setting_falls_back_to_default`, `test_get_setting_reads_env_when_no_db_row`, `test_delete_resets_to_env` pass; full pre-existing test suite shows zero new failures vs. main |
| 9 | The application falls back to `.env` values when no DB override exists | PASS | Same as #8 plus `test_resolve_effective_source_attribution` asserts `source` switches `default → env → db` correctly |
| 10 | Existing tests continue to pass and new settings tests are added | PASS | New tests added: `tests/test_runtime_settings_db.py` (8), `tests/test_runtime_settings_registry.py` (12), `tests/test_control_api_settings.py` (10), plus `test_settings_router_is_registered` smoke; all 30 + 1 new tests pass. Pre-existing failures unchanged vs. main |

### Additional V1-fix criteria (from `runs/T215/fixes/plan-fix-secrets-readonly-and-global-postgres-scope.md`)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| F1 | `PUT /api/settings/OPENAI_API_KEY` rejected and no raw secret persisted | PASS | `test_sensitive_put_is_rejected` returns 403 and asserts the secret was never written to the DB; `set_setting` raises `SensitiveSettingWriteError` on sensitive keys (`runtime_settings.py:329-333`) |
| F2 | Sensitive rows show `editable=false` and are non-editable in UI | PASS | `resolve_effective_setting` sets `editable=False` for sensitive specs (`runtime_settings.py:280`); UI shows "read-only in V1" copy and no edit button (`GlobalSettingsPage.jsx:222-225`) |
| F3 | Postgres `runtime_settings` is global-only (no project_id column) | PASS | DDL in `runtime_db_pg.py:234-242` uses `key TEXT PRIMARY KEY`; helpers signatures match SQLite (no `project_id` argument). Backend-agnostic `get_setting(db_path, key)` confirmed. |

## Anomalies observed

None blocking. Two minor non-blocking observations:

- The implementation review's claim that only ~9 pre-existing failures
  exist on main is incorrect (the real baseline is 115). It does not
  change the verdict — every failure reproduces identically on main —
  but the review's regression baseline should be tightened next time.
- Postgres backend is not exercised by the test suite (no live PG
  fixtures in CI). The Postgres helpers are wired but only validated by
  shape inspection of the DDL and helper signatures, not by an
  integration test. This matches the existing project's testing
  posture (other Postgres-only helpers are similarly untested).

## Validation

Implementation satisfies every ticket acceptance criterion and the
secrets-read-only / Postgres-global fixes mandated by the plan review.
No regressions vs. main.
