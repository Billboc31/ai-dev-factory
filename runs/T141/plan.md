Plan written to `runs/T141/plan.md`. Here's what it covers:

**Root cause:** `stop()` (line 176) only calls `docker compose down` — it never terminates the supervisor, releases the port slot, or cleans pid/lock files. All the helper methods needed (`_terminate_sandbox_supervisor`, `_release_slot`) already exist.

**Seven concrete changes:**

1. **Fix `stop()`** — add supervisor termination, slot release, and `*.pid`/`*.lock` removal from `sandbox_runtime_root`
2. **Add `restart()`** — thin wrapper: `stop()` then `start()`
3. **Add `refresh()`** — stateless `_read_state()` with no side effects
4. **Two new routes** in `routes/sandbox.py` — `POST /sandboxes/{id}/restart` and `/refresh`
5. **`SandboxRunSummary` enrichment** — add `runtime_root` and `uptime_seconds` fields, populate in `_parse_sandbox_state()`
6. **Three proxied dashboard endpoints** — stop/restart/refresh on `/runtime-dashboard/sandbox-runs/{id}/...`
7. **Six test cases** — supervisor mock, slot release, pid/lock file cleanup, restart transitions, refresh no-side-effects, concurrent isolation
