Implementation complete. Here's a summary of what was done:

---

**Files modified:**

- **`services/supervisor/main.py`** — Full rewrite: added `DaemonState` dataclass, module globals (`_daemon_state`, `_daemon_proc`, `_voluntary_stop`, `_daemon_exec_cmd`), `_spawn_daemon()` helper, `_check_and_maybe_restart()` sync monitor step, `_monitor_daemon()` async background task, FastAPI `lifespan` (init from PID file + task management). Updated `daemon_status()` to return all new fields + stale PID recovery, `daemon_start()` to accept `restart_policy`, `daemon_stop()` to set `_voluntary_stop` flag.

- **`services/control_api/models/schemas.py`** — Extended `DaemonStatus` with 6 optional fields: `last_exit_code`, `last_exit_time`, `last_error`, `exit_unexpected`, `restart_count`, `restart_policy`.

- **`services/control_api/services/daemon_manager.py`** — `get_status()` now forwards all new fields from the supervisor `/daemon/status` response.

- **`apps/dashboard/src/pages/DaemonPage.jsx`** — Added `CrashBanner` component (shown when `exit_unexpected=true`, displays exit code / time / restart count) and a "Restarting…" badge inside the status card when `restart-on-crash` policy is active.

- **`tests/supervisor/test_supervisor.py`** — Added 4 new tests (8 total, all pass): unexpected exit detection, stale PID recovery, restart-on-crash policy, voluntary stop not flagged unexpected.

- **`apps/dashboard/tests/DaemonPage.test.jsx`** — Added 2 new tests (10 total, all pass): crash banner shown / not shown on normal stop.
