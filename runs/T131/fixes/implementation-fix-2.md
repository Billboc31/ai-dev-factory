# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T131/reviews/implementation-review.md
- generated at: 2026-05-21T22:27:42Z

---

Now I have all I need. Let me write the structured review.

---

## Review — T131: Supervisor Daemon Persistence and Unexpected Exit Handling

### Summary

The implementation is complete, cohesive, and covers all seven acceptance criteria. The supervisor architecture is well-separated: daemon state lives in the supervisor process, the control-API delegates cleanly, and the dashboard exposes crash metadata. Tests cover the critical paths.

Below I document one notable correctness gap, a durability limitation, and minor observations.

---

### 1. Correctness Relative to Ticket Requirements

| Acceptance criterion | Status | Notes |
|---|---|---|
| Daemon survives after API request | ✅ | `start_new_session=True` on all Popen calls |
| Unexpected exits detected and reported | ✅ | Monitor polls `_is_alive()` every 5 s, sets `exit_unexpected` |
| Dashboard shows crash state | ✅ | `CrashBanner` with exit code, time, restart count |
| Restart-on-crash relaunches | ✅ | `_check_and_maybe_restart()` + `_spawn_daemon()` |
| Stale PID recovered automatically | ✅ | Both lifespan startup and `/daemon/status` handle it |
| Supervisor status API exposes runtime/crash info | ✅ | 10-field response from `GET /daemon/status` |
| Existing daemon workflows preserved | ✅ | All four start paths remain functional |

---

### 2. Notable Issue — `_daemon_state.pid` not cleared in `daemon_stop()` (main.py:400–416)

After `daemon_stop()` sends SIGTERM, `_daemon_state.pid` retains the old PID. The PID file is removed but the in-memory state is not updated until the monitor's next 5-second cycle.

**Consequence:** if a caller invokes `POST /daemon/start` immediately after `POST /daemon/stop`, `daemon_start()` reads `_daemon_state.pid` (old PID), calls `_is_alive(pid)` while the process is still dying, and returns `{"ok": False, "error": "already_running"}`. This window is typically milliseconds but it is observable from the dashboard (Stop → immediate Start).

**Recommended fix** — clear `_daemon_state.pid` in `daemon_stop()` before returning:

```python
os.kill(pid, signal.SIGTERM)
_daemon_state.pid = None  # add this line
_daemon_state.started_at = None  # and this
_remove_pid_file()
```

This matches the semantics (`_daemon_proc` is not cleared either, but the monitor handles that).

---

### 3. Durability Limitation — `_daemon_exec_cmd` and `restart_policy` lost on supervisor restart (main.py:237–257)

If the supervisor process itself restarts (crash or redeploy) while a daemon is running with a non-default `exec_cmd` and `restart_policy="restart-on-crash"`:

- The lifespan reconnects to the live daemon via the PID file — correct.
- `_daemon_exec_cmd` reverts to `"claude --dangerously-skip-permissions"` — wrong.
- `_daemon_state.restart_policy` reverts to `"no-restart"` — crash recovery silently disabled.

The ticket says "restart-on-crash policy successfully relaunches the daemon" — this fails after a supervisor restart if custom parameters were used.

**Recommended fix** — persist `exec_cmd` and `restart_policy` in the PID file and reload them in lifespan:

```python
# _write_pid_file: add exec_cmd and restart_policy to JSON
# lifespan: restore _daemon_exec_cmd and _daemon_state.restart_policy from file
```

This is a 3-line change to both `_write_pid_file` and the lifespan startup block.

---

### 4. Minor Observations

**a. No restart backoff or max-retry cap** (main.py:214–226)  
If the daemon binary crashes immediately on start (bad config, missing dependency), the monitor will loop respawning it every 5 seconds forever. Not a ticket requirement, but worth noting as a follow-up.

**b. `_check_and_maybe_restart()` blocks the event loop** (main.py:229–232)  
This sync function is called directly from async `_monitor_daemon()`. It calls `_is_alive()` (fast syscall) and potentially `_spawn_daemon()` (file I/O, `Popen`). For a single-process supervisor with no concurrent load, this is benign in practice, but technically incorrect asyncio usage.

**c. `supervisor_available` and `supervisor_url` fields on `DaemonStatus` are never populated** (schemas.py:18–19, daemon_manager.py:231–267)  
These two fields exist in the schema but `get_status()` never sets them. They are always `None`. Either populate them or remove them to avoid dead schema surface.

**d. "Restarting…" badge has no test coverage** (DaemonPage.jsx:165–169, DaemonPage.test.jsx)  
The badge is correct: it appears when `restart_policy="restart-on-crash" && exit_unexpected && !running`. No test exercises this. Low-risk since the CrashBanner test covers the surrounding logic.

---

### 5. Code Quality

- `services/supervisor/main.py` is clean, well-factored, and all state mutations are in one place.
- PID file format is stable (JSON, versioned-safe).
- `_voluntary_stop` flag is straightforward and correctly reset after use.
- The four-path delegation in `daemon_manager.start()` is explicit and well-documented.
- Tests cover all acceptance criteria behaviors with proper monkeypatching.

---

### Decision

The two issues raised in §2 and §3 are real correctness gaps. Issue §2 (stop/start race) is directly observable from the dashboard. Issue §3 (state lost on supervisor restart) violates the restart-on-crash acceptance criterion in a specific but realistic scenario.

Both fixes are small and low-risk. The implementation should address them before merge.

IMPLEMENTATION_FIX_REQUIRED
