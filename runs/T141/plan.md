The plan is written to `runs/T141/plan.md`. Here's what it covers:

**Core problem identified:** `stop()` at line 176 only runs `docker compose down` — it never calls `_terminate_sandbox_supervisor()`, never calls `_release_slot()`, and never cleans pid/lock files.

**Three changes to `sandbox_manager.py`:**
1. Fix `stop()` — add supervisor termination, pid/lock cleanup, and port release
2. Add `restart()` — stop + start
3. Add `refresh()` — stateless re-read of state.json

**Two new endpoints in `routes/sandbox.py`:**
- `POST /sandboxes/{id}/restart`
- `POST /sandboxes/{id}/refresh`

**Dashboard enrichment in `routes/runtime_dashboard.py`:**
- `SandboxRunSummary` gains `runtime_root` and `uptime_seconds`
- Three new proxied lifecycle endpoints (stop/restart/refresh)

**Tests** cover the supervisor SIGTERM mock, port release, pid/lock cleanup, restart transitions, refresh no-side-effects, and concurrent safety.
