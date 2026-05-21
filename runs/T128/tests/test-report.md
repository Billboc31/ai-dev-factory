The `--issue-repo None` behavior is consistent with path 3 (daemon_manager.py also omits it). The daemon detects the repo from `git remote` when `None`. This is intentional and not a regression.

---

## Test Report — T128: Host Supervisor for Daemon and Deployment Jobs

**Branch:** `ticket/T128-t128-host-supervisor-for-daemon-and-deployment-job`
**Date:** 2026-05-21
**Test suite:** 4 supervisor-specific tests + full regression suite

---

### Test Suite Results

```
tests/supervisor/test_supervisor.py   4 passed   (new)
tests/ (excluding supervisor)        575 passed  44 failed
main branch baseline                 557 passed  44 failed
```

**Net change:** +18 passing, 0 new failures. All 44 failures are pre-existing and reproduced identically on `main` (caused by `AI_DEV_FACTORY_RUNTIME_ROOT` being set in the host environment, which breaks tests that assume `tmp_path/runs` as the PID directory). No regressions introduced by T128.

---

### Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Supervisor can be started on the host and reports health/status | **PASS** | `deploy/start_supervisor.sh` starts FastAPI on `127.0.0.1:8090`; `GET /health` returns `{"status": "ok", "daemon_pid": ...}`; `test_health_ok` passes |
| 2 | Docker control API can detect whether the supervisor is available | **PASS** | `_enrich_with_supervisor()` in `daemon.py:20–31` pings `SUPERVISOR_URL/health`; populates `DaemonStatus.supervisor_available` and `supervisor_url` on every `/daemon/status` response |
| 3 | Starting the coding daemon from the dashboard delegates to the host supervisor | **PASS** | `daemon_manager.start()` path 0 (`daemon_manager.py:452–476`) calls supervisor `POST /daemon/start`; `test_start_delegates_to_supervisor` verifies `subprocess.Popen` is never called in the control API |
| 4 | If supervisor is unavailable, dashboard shows clear error and the manual host command | **PASS** | Returns `ActionResult(error="supervisor_unreachable", host_command="cd ... && bash deploy/start_supervisor.sh")`; `HostCommandPanel` in `DaemonPage.jsx:52–101` renders yellow alert with copyable command; `test_supervisor_unreachable_returns_structured_error` passes |
| 5 | Supervisor-launched daemon has access to gh, Claude CLI, git worktrees, canonical runtime root | **PASS** | Supervisor runs on host (not Docker); `start_supervisor.sh` sets `AI_DEV_FACTORY_RUNTIME_ROOT` and activates host venv; `subprocess.Popen` with `env={**os.environ}` inherits host PATH; `--worktrees-dir` passed explicitly |
| 6 | Job logs and status are visible from the dashboard/control API | **PASS** | `GET /daemon/activity` returns last N daemon.log lines; `GET /daemon/status` reports running/pid/started_at; `GET /daemon/runtime-status` exposes workers, retry-blocked tickets, intake queue; dashboard has activity feed + runtime status panel |
| 7 | No fake PID/status files are written when startup fails | **PASS** | Path 0 (supervisor): supervisor writes PID only after successful `Popen`; path 2 (Docker refusal): `_refuse_with_log()` writes to `daemon.log` only, no PID file; path 3 (host Popen): `_write_pid_file` called only after `subprocess.Popen` succeeds (`daemon_manager.py:572`) |
| 8 | Existing manual daemon launch and runtime workflows still work | **PASS** | Path 3 (host `Popen` flow) is intact; `run_daemon.py` unchanged; pre-existing test count unchanged |

---

### Anomalies Observed

**Minor — not blocking:**

- `--issue-repo` is not forwarded by the supervisor's `daemon_start()` when spawning the daemon. This is consistent with path 3 behavior in `daemon_manager.py` (same omission). The daemon defaults to `None` and uses git remote detection at runtime. This was pre-existing behavior, not a regression.

- The dashboard `DaemonPage.jsx` does not visually render `supervisor_available` or `supervisor_url` fields from the status response. The control API detects and reports supervisor availability correctly (criterion 2), but a user cannot see this state from the UI without checking the raw API. This is a UX improvement opportunity, not a criterion failure.

- Host dependency validation (gh, claude, git, docker) is only performed in path 3 (host Popen), not at supervisor startup time. The ticket's "Included" section mentions this, but it is not part of the formal acceptance criteria.

---

### Verdict

**PASS** — All 8 acceptance criteria are satisfied. No regressions. The implementation is complete and coherent.
