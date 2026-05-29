The implementation is complete. Here's a summary:

---

## T159 — Implementation Summary

### Changes committed (7 source files, all T159-scoped)

**`tools/agent_runner/runtime_db.py`**
- `check_and_recover_db()`: full recovery sequence (integrity_check → quarantine → `.recover` → recreate empty DB) inside `fcntl.flock(LOCK_EX)` on `<db_path>.recovery.lock`
- `_connect()` and `init_runtime_db()`: WAL mode, `busy_timeout=5000`, `synchronous=NORMAL` on every connection
- `get_db_path()`: git rev-parse-based resolution ensuring all worktrees share one global DB

**`tools/agent_runner/run_daemon.py`**
- `_ensure_db()`: calls `check_and_recover_db()` at startup before any write
- `_acquire_daemon_singleton()`: `LOCK_EX|LOCK_NB` on `daemon-singleton.lock` — second daemon exits cleanly with a clear log message
- `run_once()`/`launch_ticket()`: pass `state_dir` through so workers use the canonical state path

**`services/control_api/services/board_service.py`**
- `_load_runtime_db()` and `_try_load_runtime_db()`: now call `mod.get_db_path()` (via the loaded module) instead of constructing the path from `project_root` — fixes worktree-local DB lookup bug
- Full filesystem fallback (workers.json, state.json, .issue-intake.json) when SQLite is unavailable
- `degraded=True` propagated to `BoardResponse`

**`services/control_api/routes/runtime_dashboard.py`**
- Health endpoint simplified to use `_try_load_runtime_db()` — `sqlite_degraded` flag surfaced in `RuntimeHealth`

**`services/control_api/models/schemas.py`**
- `BoardResponse.degraded: bool = False` added

**`tests/test_runtime_db.py`** — 19 tests: healthy DB, corrupt DB quarantine, concurrent-lock serialization (4 threads), pragma verification, CRUD persistence

**`tests/test_run_daemon.py`** — updated `test_run_once_calls_launch_for_auto_runnable_state` to expect `state_dir=runs` in the `launch_ticket` call

### Verification
- All 19 `test_runtime_db.py` tests pass
- All 42 `test_runtime_dashboard_api.py` tests pass
- All 3 `test_environment_routes.py` regressions fixed (T158 file restorations committed)
- Full suite: 49 pre-existing failures remain (same as baseline, none introduced by T159)
