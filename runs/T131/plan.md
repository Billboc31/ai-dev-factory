Here is the plan:

---

## Objective

Add a background monitoring loop to the supervisor so it detects unexpected daemon exits, preserves exit metadata, and supports a configurable restart policy; surface this state through the supervisor and control-API status endpoints and the dashboard.

## Included

### `services/supervisor/main.py`

- Add an in-memory `DaemonState` dataclass with fields: `pid`, `started_at`, `last_exit_code`, `last_exit_time`, `last_error`, `restart_count`, `restart_policy` (`"no-restart"` | `"restart-on-crash"`), `exit_unexpected`.
- Replace bare PID-file reads with reads/writes of `_daemon_state` (PID file stays as on-disk record; `_daemon_state` is the in-memory mirror).
- Add `_monitor_daemon()` asyncio background task (5 s polling):
  - Detect when the process is gone, record `last_exit_code`, `last_exit_time`, `last_error`, and set `exit_unexpected = True` when the stop was not voluntary.
  - If `restart_policy == "restart-on-crash"` and `exit_unexpected`: increment `restart_count` and re-spawn.
- Wire the background task into FastAPI `lifespan`.
- `POST /daemon/start` accepts optional `restart_policy` (defaults to `"no-restart"`).
- `POST /daemon/stop` sets an internal `_voluntary_stop` flag before SIGTERM so the monitor does not flag the exit as unexpected.
- `GET /daemon/status` returns all `DaemonState` fields.

### `services/control_api/models/schemas.py`

- Extend `DaemonStatus` with: `last_exit_code`, `last_exit_time`, `last_error`, `exit_unexpected`, `restart_count`, `restart_policy` (all optional).

### `services/control_api/services/daemon_manager.py`

- In `status()`, forward the new fields from the supervisor `/daemon/status` response into the returned `DaemonStatus`.

### `apps/dashboard/src/pages/DaemonPage.jsx`

- Add a crash-state banner shown when `exit_unexpected == true` (displays exit code, time, restart count).
- Add a "Restarting…" badge when restart policy is active and daemon is not yet back up.

### Tests (`tests/supervisor/test_supervisor.py`)

- `test_unexpected_exit_detected()` — kill daemon, assert `exit_unexpected=true`.
- `test_stale_pid_recovery()` — non-existent PID → `running=false`, file removed.
- `test_restart_on_crash_policy()` — crash with policy set → `restart_count=1`, re-spawned.
- `test_voluntary_stop_not_flagged_unexpected()` — stop via API → `exit_unexpected=false`.

### Tests (`apps/dashboard/tests/DaemonPage.test.jsx`)

- `test_crash_banner_shown()` / `test_no_crash_banner_on_normal_stop()`.

## Excluded

- Persisting `DaemonState` to disk across supervisor restarts (in-memory only).
- Configuring restart policy via env var or config file (API-only).
- Max-restart-count cap or exponential back-off (follow-up ticket).
- Deployment supervision, multi-process orchestration, remote hosts, Kubernetes/systemd.
- Forwarding `restart_policy` through the control-API `POST /daemon/start` (supervisor is the policy owner).

## Acceptance criteria

- `GET /daemon/status` (supervisor port 8090) always includes `last_exit_code`, `last_exit_time`, `last_error`, `exit_unexpected`, `restart_count`, `restart_policy`.
- `kill -9 <daemon_pid>` → next status poll returns `exit_unexpected=true` with a non-null `last_exit_code`.
- `restart_policy="restart-on-crash"`: daemon relaunched and `restart_count` incremented; `"no-restart"`: daemon stays down.
- `POST /daemon/stop` → `exit_unexpected=false`.
- Stale PID file cleaned on first `GET /daemon/status`; returns `running=false`.
- Control-API `GET /daemon/status` propagates `exit_unexpected`, `last_exit_code`, `last_exit_time`, `restart_count` from supervisor when supervisor is available.
- Dashboard renders a visible crash banner when `exit_unexpected=true`.
- All 4 new supervisor tests and 2 new dashboard tests pass; existing tests unaffected.

---

Plan written to `runs/T131/plan.md`.
