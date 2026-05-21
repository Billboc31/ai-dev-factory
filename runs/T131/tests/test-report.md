All checks are complete. Here is the test report.

---

## Test Report — T131: Supervisor Daemon Persistence and Unexpected Exit Handling

**Branch:** `ticket/T131-t131-supervisor-daemon-persistence-and-unexpected`  
**Date:** 2026-05-22

---

### Test Execution Summary

| Suite | Tests | Result |
|---|---|---|
| `tests/supervisor/test_supervisor.py` | 10 | **10 passed** |
| `apps/dashboard/tests/DaemonPage.test.jsx` | 10 | **10 passed** |
| **Total** | **20** | **20 passed, 0 failed** |

---

### Acceptance Criteria

**1. The daemon continues running after dashboard/API requests complete.**  
`PASS` — `_spawn_daemon` uses `start_new_session=True` (supervisor/main.py:165), which fully detaches the child process from the parent session. The daemon survives API server shutdown.

**2. Unexpected daemon exits are detected and reported.**  
`PASS` — `_check_and_maybe_restart()` runs in a 5-second polling loop. When the PID is dead and `_voluntary_stop` is False, it sets `exit_unexpected=True`, records `last_exit_code`, `last_exit_time`, and `last_error`. Covered by `test_unexpected_exit_detected`.

**3. Dashboard clearly shows daemon crash state.**  
`PASS` — `CrashBanner` renders when `exit_unexpected === true` with "Daemon crashed unexpectedly", exit code, exit time, and restart count. The "Restarting…" badge appears when `restart_policy === 'restart-on-crash'` and the daemon is crashed but not yet recovered. Covered by `test_crash_banner_shown` and `test_no_crash_banner_on_normal_stop`.

**4. Restart-on-crash policy successfully relaunches the daemon.**  
`PASS` — When `exit_unexpected` is True and `restart_policy == "restart-on-crash"`, `_check_and_maybe_restart()` increments `restart_count` and calls `_spawn_daemon`. Covered by `test_restart_on_crash_policy`.

**5. Stale PID files are recovered automatically.**  
`PASS` — Both `GET /daemon/status` and the lifespan handler call `_is_alive(pid)` on any PID found in the file; if the process is dead, the PID file is removed and `running=False` is returned. Covered by `test_stale_pid_recovery`.

**6. Supervisor status API exposes runtime and crash information.**  
`PASS` — `GET /daemon/status` returns `running`, `pid`, `started_at`, `last_exit_code`, `last_exit_time`, `last_error`, `exit_unexpected`, `restart_count`, `restart_policy`. The control-API `DaemonStatus` schema mirrors all these fields and forwards them when a supervisor is available.

**7. Existing daemon workflows continue to work.**  
`PASS` — All pre-existing tests (start, stop, status, heading render, start/stop/restart buttons, error banner) pass without regression. No breaking changes to the API shape.

---

### Observations

- **No blocking issues found.** All acceptance criteria are met by the implementation and verified by the test suite.
- **One noted limitation (non-blocking):** Exit metadata (`last_exit_code`, `last_exit_time`, `exit_unexpected`) is stored only in-memory on the supervisor process. If the supervisor itself is restarted, this metadata is lost. This is consistent with the stated design decision ("not persist across restarts") and is not a regression from the previous behavior.
- **Voluntary stop race:** The `_voluntary_stop` flag is set before `os.kill` and cleared after the stop is confirmed. This correctly prevents false crash detection during API-initiated stops, as verified by `test_voluntary_stop_not_flagged_unexpected`.

---

**Verdict: PASS** — The implementation satisfies all acceptance criteria. No regressions observed.
