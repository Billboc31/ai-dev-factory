## Objective

Fix the incomplete `stop()` implementation and add `restart`, `refresh`, and destroy lifecycle operations for sandbox environments, with corresponding API endpoints and dashboard enrichments, so sandboxes can be safely stopped, restarted, and destroyed without leaving dangling processes or stale lock/pid files.

## Included

**`sandbox_manager.py` — fix `stop()` (line 176):**
- Add `_terminate_sandbox_supervisor(state)` call
- Clean stale `*.pid` and `*.lock` files from `sandbox_runtime_root` (per-file OSError catch)
- Do NOT call `_release_slot()` on stop — port slot is retained so `restart()` reuses the same ports

**`sandbox_manager.py` — add `restart()`:**
- `stop()` then `start()`, return state from `start()`

**`sandbox_manager.py` — add `refresh()`:**
- `_read_state()` and return it — no side effects, no subprocess

**`routes/sandbox.py` — two new endpoints:**
- `POST /{sandbox_id}/restart` → `manager.restart()`, 200 or 404
- `POST /{sandbox_id}/refresh` → `manager.refresh()`, 200 or 404

**`routes/runtime_dashboard.py` — enrich `SandboxRunSummary` (line 81):**
- Add `runtime_root: str | None` (from `raw.get("sandbox_runtime_root")`)
- Add `uptime_seconds: float | None` (computed from `started_at` when status is `running`)

**`routes/runtime_dashboard.py` — two new dashboard lifecycle endpoints:**
- `POST /runtime-dashboard/sandbox-runs/{id}/stop`
- `POST /runtime-dashboard/sandbox-runs/{id}/restart`

**Tests in `test_sandbox_manager.py` and `test_sandbox_routes.py`:** stop supervisor mock, pid/lock cleanup, port slot retention, restart transitions, refresh no-side-effects, new endpoint 200/404 cases.

## Excluded

- Generic runtime topology model, `sandbox-profile.yml`, component DAG, health polling
- Frontend UI changes (JS/React)
- Distributed orchestration, Kubernetes, cloud deployment
- AI auto-healing loops
- Log preservation on delete

## Acceptance criteria

- `stop()` calls `_terminate_sandbox_supervisor()` and removes stale `*.pid`/`*.lock` files
- `stop()` does not remove the port slot from the registry
- `restart()` transitions sandbox from stopped → running
- `refresh()` returns current disk state without subprocess calls
- `POST /sandboxes/{id}/restart` and `/refresh` return 200 or 404
- `GET /runtime-dashboard/sandbox-runs` includes `runtime_root` and `uptime_seconds`
- Dashboard stop/restart endpoints work end-to-end
- All new and existing tests pass
- Two concurrent sandboxes remain isolated
