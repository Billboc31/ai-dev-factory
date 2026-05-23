33/33 tests pass. Here's what was implemented:

**Files modified:**

- `services/control_api/services/sandbox_manager.py`
  - `stop()`: now calls `_terminate_sandbox_supervisor()` + cleans `*.pid`/`*.lock` from `sandbox_runtime_root` before updating status; port slot is retained
  - `restart()` added: `stop()` → `start()`, returns running state
  - `refresh()` added: reads and returns current disk state with no subprocess calls

- `services/control_api/routes/sandbox.py`
  - `POST /{sandbox_id}/restart` → `manager.restart()`, 200 or 404
  - `POST /{sandbox_id}/refresh` → `manager.refresh()`, 200 or 404

- `services/control_api/routes/runtime_dashboard.py`
  - `SandboxRunSummary` enriched with `runtime_root: str | None` and `uptime_seconds: float | None`
  - `_parse_sandbox_state()` computes `uptime_seconds` from `started_at` when status is `running`
  - `POST /runtime-dashboard/sandbox-runs/{id}/stop` endpoint added
  - `POST /runtime-dashboard/sandbox-runs/{id}/restart` endpoint added

- `tests/test_sandbox_manager.py`: 5 new tests (supervisor SIGTERM, pid/lock cleanup, port slot retention, restart transitions, refresh no-subprocess)
- `tests/test_sandbox_routes.py`: 4 new tests (restart 200/404, refresh 200/404)
