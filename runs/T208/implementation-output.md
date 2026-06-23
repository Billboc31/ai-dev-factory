## Summary

The full T208 implementation was already on the branch from a prior coder run (`TEST_COMPLETE` checkpoint commits exist before today's `pre-sync auto-commit` commits). Attempt 4 was triggered because previous attempts produced provider 500 errors *after* the work had been written and committed. I audited every plan section against the working tree and ran the tests to confirm the implementation is intact and correct.

### Plan coverage (all ✓)

| § | Change | Status |
|---|---|---|
| 1 | `intelligence.py` & `supervisor/main.py` `_bg` wrappers persist `failed`/`bg_thread_crash` on escaping exceptions; analyzer has top-level `try/finally` guard + `started_at` write | done |
| 2 | `_run_ai_subprocess` uses `Popen` + `communicate(timeout=…)` + `kill()` + drain; `_ANALYSIS_TIMEOUT` env-tunable (default 120 s) | done |
| 3 | SQLite: 4 new TEXT columns + idempotent `PRAGMA table_info`-driven `ALTER TABLE` migration | done |
| 4 | Postgres: 4 new columns in `_DDL` + `ADD COLUMN IF NOT EXISTS` migration block | done |
| 5 | Every persistence path writes `completed_at` or `failed_at`+`failure_origin` (`timeout`/`nonzero_rc`/`json_parse`/`exception`/`finally_guard`/`bg_thread_crash`/`reaper-confirmed`/`reaper-stale`) | done |
| 6 | Reaper preserves prior `analysis_summary` + sets `failure_origin="reaper-confirmed"`; writes `failed_at` uniformly | done |
| 7 | `TicketIntelligence` schema + dashboard panel render new fields | done |
| 8 | All `intel.*` log lines emitted in plan-mandated order | done |
| 9 | Tests added per plan + Postgres parity tests (fallback path — repo has no live PG infra) | done |

### Files modified (vs. main)
- `services/control_api/routes/intelligence.py`, `services/supervisor/main.py`
- `services/control_api/models/schemas.py`
- `tools/agent_runner/ticket_intelligence_analyzer.py`, `ticket_intelligence_recovery.py`
- `tools/agent_runner/runtime_db.py`, `runtime_db_pg.py`
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx`
- `tests/test_ticket_intelligence_analyzer.py`, `tests/test_ticket_intelligence_recovery.py`, `tests/test_ticket_intelligence_api.py`, `tests/test_runtime_db_pg.py`

### Verification
- `pytest tests/test_ticket_intelligence_*.py tests/test_runtime_db_pg.py`: **53 passed, 1 failed**
- The 1 failure (`test_default_backend_is_sqlite`) is pre-existing on `main` — reverified by reverting all T208-touched files and re-running the test, which still fails. Not caused by this ticket.
- `py_compile` clean on all touched Python files. `ruff` not installed in this venv, so no lint output to report.

### Limitations
- Postgres lifecycle round-trip is verified via DDL/migration-string assertions (the fallback path explicitly allowed by plan §9), not a live Postgres connection — no PG test infra is wired up in this repo.
- The pre-existing `test_default_backend_is_sqlite` failure is out of T208's scope and left untouched.
