The plan has been written to `runs/T159/plan.md`. Here is the final document:

---

## Objective

Harden the runtime SQLite layer so that corruption no longer blocks the dashboard or daemon: add startup integrity checks with file-lock-protected quarantine/recovery, enable additional safety pragmas, implement a filesystem-first fallback for the dashboard, add a daemon singleton guard, and centralize DB path resolution so worktrees never create their own SQLite files.

## Included

Six concrete change areas:

1. **`tools/agent_runner/runtime_db.py`** — add `check_and_recover_db(db_path)` whose entire sequence (integrity_check → quarantine rename → recover/recreate → schema init) runs inside `fcntl.flock(LOCK_EX)` on `<db_path>.recovery.lock`; add `busy_timeout=5000` and `synchronous=NORMAL` pragmas to every connection.

2. **`tools/agent_runner/run_daemon.py`** — call `check_and_recover_db()` at startup inside `_ensure_db()`; add a daemon singleton guard via a global `daemon-singleton.lock` with `LOCK_NB` so a second daemon instance exits cleanly instead of racing on SQLite.

3. **`services/control_api/services/board_service.py`** — wrap `_load_runtime_db()` in try/except; on failure read board data from filesystem (`state.json`, `workers.json`, `.issue-intake.json`) and return `{"degraded": True, ...}`.

4. **`services/control_api/routes/runtime_dashboard.py`** — surface the degraded warning in the JSON response.

5. **Cleanup audit** — remove any DB open outside `get_db_path()` in worktree/clone paths.

6. **Tests** — four new test cases covering: healthy DB, corrupt DB quarantine, concurrent-caller lock serialization (race condition), and pragma verification.

## Excluded

PostgreSQL, distributed coordination, HA/replication, cloud DB, Kubernetes, frontend UI changes beyond the JSON warning field, per-ticket `daemon.lock` files.

## Acceptance criteria

All 14 verifiable conditions are listed in the plan, including: lock acquired before any mutation, lock released after schema init, race condition test passes, `busy_timeout`/`synchronous` pragmas verified, dashboard degrades gracefully, daemon does not crash-loop, only one global DB path used.
