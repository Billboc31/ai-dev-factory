All 10 tests pass. Here's a summary of what changed:

**Fix 1 — stop/start race** (`daemon_stop()`, lines 411–412):  
Added `_daemon_state.pid = None` and `_daemon_state.started_at = None` immediately after SIGTERM, before returning. The window where a rapid Stop→Start would see a stale in-memory PID and return `already_running` is eliminated.

**Fix 2 — state lost on supervisor restart** (3 locations):  
- `_write_pid_file()` — now accepts and persists `exec_cmd` and `restart_policy` in the JSON.  
- `_spawn_daemon()` — passes both values to `_write_pid_file`.  
- `lifespan` — restores `_daemon_exec_cmd` and `_daemon_state.restart_policy` when reconnecting to a live daemon.  
- `daemon_status()` — same restore logic in the stale-PID-recovery path for completeness.

**Two new tests** (test 9 and 10) verify these behaviors directly.
