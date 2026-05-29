All 7 tasks complete. Here's a summary of what was implemented:

---

## Summary

### Files modified

**`tools/agent_runner/runtime_db.py`**
- Added `import fcntl`
- Added `PRAGMA busy_timeout=5000` and `PRAGMA synchronous=NORMAL` to both `init_runtime_db()` and `_connect()`
- Added `check_and_recover_db(db_path)` — full integrity-check → quarantine rename → `.recover` → recreate sequence, protected by `fcntl.flock(LOCK_EX)` on `<db_path>.recovery.lock`

**`tools/agent_runner/run_daemon.py`**
- Added `import errno, fcntl`
- Exposed `_rdb_check_and_recover` from runtime_db module
- Updated `_ensure_db()` to call `_rdb_check_and_recover(db_path)` before `init_runtime_db`
- Added `_acquire_daemon_singleton(lock_dir)` — `LOCK_EX|LOCK_NB` flock on `daemon-singleton.lock`; returns `False` if another daemon process holds the lock
- Added singleton guard call in `main()` before `_cleanup_stale_workers`, exits with code 1 cleanly

**`services/control_api/models/schemas.py`**
- Added `degraded: bool = False` to `BoardResponse`

**`services/control_api/services/board_service.py`**
- Added `_try_load_runtime_db()` helper returning `(mod, db_path, degraded)` — distinguishes "DB absent" from "DB exists but broken"
- Wrapped all three SQLite query calls (`list_workers`, `list_ticket_runtime`, `list_issue_intake`) in individual try/except blocks; each falls back to filesystem and sets `degraded=True`
- Returns `BoardResponse(columns=..., degraded=degraded)`

**`services/control_api/routes/runtime_dashboard.py`**
- Added `sqlite_degraded: bool = False` to `RuntimeHealth` model
- Added SQLite degraded detection in `get_runtime_health()` — checks DB existence then tries `_load_runtime_db`; sets `sqlite_degraded=True` on failure

**`tests/test_runtime_db.py`**
- Added 4 new tests: healthy DB passes unchanged, corrupt DB is quarantined and recreated, 4 concurrent callers serialize correctly, and `_connect()` applies `busy_timeout=5000` / `synchronous=NORMAL`

All 19 `test_runtime_db.py` tests pass; 2 pre-existing `test_run_daemon.py` failures are environment-level issues unrelated to these changes.
