All three fixes are complete. Here's a summary:

---

**Files modified:**

**`tools/agent_runner/run_daemon.py`**
- Removed dead `_commit_after_intake` function (confirmed no callers existed)
- Added `_cached_db_path()` + `_ensure_db()` — DB path resolved via subprocess exactly once per daemon process, init also runs once
- Replaced all `_rdb_get_db_path()` / `_rdb_init()` call sites with `_cached_db_path()` or `_ensure_db()`
- All `except Exception: pass` blocks now log the exception via `_log()`

**`services/control_api/services/board_service.py`**
- Added `sqlite_ticket_states` loading from `ticket_runtime` table right after filesystem scan
- Rewrote kanban loop: iterates `all_ticket_ids = sorted(filesystem ∪ SQLite)`, preferring SQLite state for column placement; falls back to `state.json` only when ticket is absent from SQLite
- SQLite-only tickets (no `state.json` on disk) now appear on the board correctly
