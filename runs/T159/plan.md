Plan saved to `runs/T159/plan.md`. Here is the output:

---

## Objective

Harden the runtime SQLite layer so corruption never blocks dashboard visibility or daemon operation: add startup integrity checks with automatic quarantine, add missing hardening pragmas, expose a degraded-mode flag to the board UI, and confirm the single-global-DB invariant is already enforced.

## Included

### 1. `tools/agent_runner/runtime_db.py` — hardening pragmas
- Add `PRAGMA busy_timeout=5000` and `PRAGMA synchronous=NORMAL` to both `init_runtime_db()` and `_connect()` (WAL mode is already set; these two are missing).

### 2. `tools/agent_runner/runtime_db.py` — startup integrity check + quarantine
- Add `check_and_recover_db(db_path: Path) -> bool`:
  - Open connection, run `PRAGMA integrity_check`.
  - If result is not `[('ok',)]`: rename to `<stem>.corrupted-<YYYYMMDDTHHmmss>.sqlite`; log `"runtime DB corrupted -> entering degraded mode"`.
  - Attempt recovery via iterdump into a new DB; if impossible, recreate empty DB from schema.
  - Return `True` if healthy or recovered, `False` if degraded.
- File rename is atomic on POSIX; function is safe for concurrent callers.

### 3. `tools/agent_runner/run_daemon.py` — use integrity check at startup
- In `_ensure_db()`: call `check_and_recover_db(db_path)` before `_rdb_init()`.
- Add module-level `_DB_DEGRADED: bool = False`; set to `True` on corruption.
- Improve singleton log: emit `"daemon already running (pid=<N>) — exiting to avoid concurrent SQLite writers"` when live PID detected.

### 4. `services/control_api/models/schemas.py` — extend `BoardResponse`
- Add `sqlite_degraded: bool = False` field.

### 5. `services/control_api/services/board_service.py` — surface degraded state
- Catch `sqlite3.DatabaseError` explicitly and log at `WARNING` level (not silent `pass`).
- Set `sqlite_degraded = True` when SQLite is unavailable or throws; include in `BoardResponse`.

### 6. `apps/dashboard/src/pages/BoardPage.jsx` — degraded-mode banner
- When `sqlite_degraded` is `true`, render a visible warning banner: _"SQLite runtime database unavailable — showing filesystem-derived state."_

### 7. Worktree/clone DB audit (read-only)
- Grep for secondary `sqlite3.connect` / `init_runtime_db` calls that could create a DB under `worktrees/` or `clones/`; fix any found, or add a comment in `get_db_path()` confirming the invariant holds.

## Excluded

- PostgreSQL or any other non-SQLite backend.
- Distributed or multi-user runtime coordination.
- WAL checkpoint tuning, page-size tuning, or vacuum scheduling.
- Any change to sandbox runtime roots (`sandboxes/<id>/runtime/`).
- Shell `.recover` integration if stdlib-only approach succeeds.
- `runtime_dashboard.py` routes — already filesystem-first.
- Daemon tick loop, retry policies, or ticket execution flow.

## Acceptance criteria

- `PRAGMA busy_timeout=5000` and `PRAGMA synchronous=NORMAL` present in `_connect()` and `init_runtime_db()`.
- `PRAGMA integrity_check` runs at daemon startup; corrupt DB is quarantined and a fresh DB is created automatically.
- Daemon log contains `"runtime DB corrupted -> entering degraded mode"` on integrity failure.
- `BoardResponse.sqlite_degraded` is `true` when SQLite is unavailable or corrupt.
- Board API returns HTTP 200 with filesystem-derived tickets when SQLite is absent or corrupt.
- Dashboard renders degraded-mode banner when `sqlite_degraded` is `true`.
- Grep confirms no secondary `ai-dev-factory.sqlite` can be created under worktrees or clones.
- Existing daemon, board, and sandbox test suites pass without regressions.
