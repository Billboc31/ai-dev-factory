All 41 ticket intelligence tests pass. Implementation complete.

## Summary

Implemented T206 to eliminate the supervisor/API DB desynchronization that left Ticket Intelligence analyses stuck in `queued`/`running`.

### Files modified
- `tools/agent_runner/runtime_db.py` — `get_db_path(project_id=...)` now resolves per-project DB paths (`RUNTIME_BASE_ROOT/<id>/.runtime/...` or `RUNTIME_ROOT/<id>/...`); new `resolve_db_path_for_project()` helper with explicit-root precedence; Postgres backend re-bound symmetrically.
- `tools/agent_runner/ticket_intelligence_analyzer.py` — added `project_id` kwarg and `intel.*` structured logs (started, subprocess, completed, failed) with 500-char truncation.
- `services/control_api/routes/intelligence.py` — shared `_resolve_db_for_project()` for GET+POST; writes `queued` to the project DB **before** delegating; persists `failed` on delegation errors; opportunistic reaper call on every GET and POST; `intel.queued`/`intel.delegated`/`intel.failed`/`intel.reaped` logs.
- `services/supervisor/main.py` — uses `resolve_db_path_for_project(project_id, project_runtime_root=...)`; initializes per-project DB before use; pre-thread try/except persists `failed`; reaper runs before the idempotency guard; structured logs added.
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx` — counts non-404 polling errors, halts after 5 consecutive failures with a clear banner.

### Files created
- `tools/agent_runner/ticket_intelligence_recovery.py` — `reap_stale_intelligence(db_path)` with `STALE_QUEUED_SECONDS=600` / `STALE_RUNNING_SECONDS=900`.
- `tests/test_ticket_intelligence_db_resolution.py` — 6 tests for project-aware path resolution.
- `tests/test_ticket_intelligence_recovery.py` — 7 tests for reaper behavior + opportunistic trigger on GET.
- `tests/test_ticket_intelligence_analyzer.py` — 4 tests for timeout / nonzero rc / bad JSON / project_id kwarg.

### Tests extended
- `tests/test_ticket_intelligence_api.py` — autouse fixture also clears `RUNTIME_BASE_ROOT`; 3 new T206 tests cover per-project DB write on POST, delegated completion visibility via GET, and persisted `failed` row on supervisor unreachable.

### Verification
`pytest tests/test_ticket_intelligence_*.py` → **41 passed**. Other failures in `test_control_api_endpoints.py` and `tests/supervisor/test_supervisor.py` are pre-existing on `HEAD` (verified via `git stash`).

### Assumptions / limits
- The recovery reaper runs only on dashboard polls (per the plan) — sufficient because the UI polls every 4 s while an analysis is active. No background daemon was added.
- I did not run the dashboard dev server or Vite build (no node_modules present in this worktree); the JSX change is a small additive React-state counter and renders in-tree.
- The opportunistic reaper scans rows in `queued`/`running` for the project DB; expected to be O(1) in practice (analyses are rarely concurrent).
