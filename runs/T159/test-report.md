# T159 — Test Report

**Date**: 2026-05-29  
**Tester**: Claude (automated)  
**Branch**: ticket/T159-t159-harden-runtime-sqlite-architecture-and-degrad

---

## Test suite

```
tests/test_runtime_db.py — 19/19 passed (0.06s)
```

All existing CRUD tests pass without regression.

---

## Acceptance criteria

### 1. Runtime dashboard still works if SQLite becomes corrupted
**PASS**

`board_service.py` wraps all three SQLite queries (`list_workers`, `list_ticket_runtime`, `list_issue_intake`) in individual `try/except` blocks. On any failure it falls back to `workers.json`, `state.json`, and `.issue-intake.json`. `BoardResponse` returns HTTP 200 with filesystem-derived data and `degraded=True`.

Verified: `board_service.py:127–238` — three independent fallback paths, each setting `degraded=True`.

---

### 2. Daemon does not enter infinite crash/retry loops on malformed DB
**PASS**

`run_daemon.py:_ensure_db()` (lines 123–137) catches all exceptions from `check_and_recover_db` and `init_runtime_db`, logs the failure, and returns `None`. All downstream DB calls are individually guarded. No exception propagates to the main daemon loop.

Verified: startup against the live DB completes cleanly with no exception.

---

### 3. Runtime state remains observable through filesystem fallback
**PASS**

`board_service.py` collects ticket state from `runs/*/state.json`, workers from `workers.json`, and issue index from `.issue-intake.json` when SQLite is unavailable. The board response is always returned; ticket cards are constructed from filesystem data alone.

---

### 4. Only one global runtime DB is used
**PASS**

`runtime_db.get_db_path()` resolves to:

```
/Users/pierrebocquet/runtime/ai-dev-factory/.runtime/ai-dev-factory.sqlite
```

Uses `git rev-parse --git-common-dir` so any worktree resolves to the same path. `AI_DEV_FACTORY_RUNTIME_ROOT` env override for Docker/production.

Verified: calling `get_db_path()` from the worktree returns the main-repo path.

---

### 5. Worktrees no longer create runtime SQLite DBs
**PASS**

Search across all worktrees:

```
find ~/runtime/ai-dev-factory/worktrees/ -path "*/.runtime/*.sqlite"
→ (no results)
```

No worktree contains a local `.runtime/` SQLite file.

---

### 6. SQLite corruption probability is significantly reduced
**PASS**

Both `init_runtime_db()` and `_connect()` apply:

```sql
PRAGMA journal_mode=WAL;        -- verified: "wal"
PRAGMA busy_timeout=5000;       -- verified: 5000ms
PRAGMA synchronous=NORMAL;      -- verified: 1 via _connect()
```

Tested with a live connection via `runtime_db._connect()`.

---

### 7. Startup integrity checks run automatically
**PASS**

`run_daemon.py:_ensure_db()` calls `check_and_recover_db(db_path)` before `init_runtime_db`. This runs `PRAGMA integrity_check` on every daemon startup. The call is guarded by `try/except` so it cannot crash the daemon.

---

### 8. Broken DBs are quarantined automatically
**PASS**

`check_and_recover_db` quarantines corrupt files with a timestamp suffix:

```
test.sqlite → test.sqlite.corrupt.20260529T083730Z
```

Functional test with a deliberately corrupt file: quarantine succeeded, fresh DB recreated, integrity check passed.

Live evidence in `.runtime/`:

```
ai-dev-factory.sqlite.corrupt.20260528-191804
ai-dev-factory.sqlite.corrupt.20260529T081740Z
```

Recovery is protected by `fcntl.LOCK_EX` on `.recovery.lock` — concurrent callers are serialized (tested in `test_check_and_recover_db_lock_serialization`).

---

### 9. Users receive explicit degraded-mode warnings
**PARTIAL FAIL**

**Backend** — correct and complete:
- `BoardResponse.degraded: bool = False` set to `True` on any SQLite failure (`schemas.py:133`, `board_service.py:135,173,236`)
- `RuntimeHealth.sqlite_degraded: bool = False` set to `True` when DB inaccessible (`runtime_dashboard.py:133,443–448`)
- Daemon logs `"[runtime_db] DB corrupt — entering degraded mode"` to stdout on integrity failure

**Frontend** — missing:
- `apps/dashboard/src/pages/BoardPage.jsx` fetches the board API (`res.data.columns`) but **ignores `res.data.degraded`** (line 91: `setColumns(res.data.columns)`)
- No warning banner is rendered when the backend reports `degraded=True`
- The ticket specified: *"SQLite runtime database unavailable / Showing filesystem-derived runtime state"* — this text is never shown to the user

The plan (step 6) and its own acceptance criteria explicitly required this frontend banner. The implementation review accepted the backend signal alone as sufficient, but a user watching the dashboard cannot see any indication that SQLite failed.

**Impact**: non-blocking — the dashboard still functions correctly. But the user has no visibility that they are seeing filesystem-derived data rather than SQLite data.

---

### 10. Existing deploy/sandbox/runtime flows continue functioning
**PASS**

All 19 `test_runtime_db.py` tests pass. No changes were made to sandbox, deploy, or route handlers beyond the three files modified for this ticket. Existing CRUD tests cover `issue_intake`, `ticket_runtime`, `workers`, and `runtime_events`.

---

## Additional verifications

### Daemon singleton guard
**PASS** — `_acquire_daemon_singleton` uses `LOCK_EX|LOCK_NB`. A second attempt correctly returns `EAGAIN`/`EACCES`. Daemon exits cleanly with code 1 if another instance holds the lock.

### Concurrent recovery safety
**PASS** — `test_check_and_recover_db_lock_serialization` spawns 4 threads against a corrupt DB. All serialize correctly; only one quarantine file is created.

### DB path from daemon
**PASS** — `run_daemon.py` uses `_rdb_get_db_path = _rdb_mod.get_db_path` (line 85); path resolution is centralized.

---

## Regressions observed

None.

---

## Summary

| Criterion | Status |
|---|---|
| Dashboard works if SQLite corrupted | ✅ PASS |
| No daemon crash loops | ✅ PASS |
| Filesystem fallback observable | ✅ PASS |
| Single global runtime DB | ✅ PASS |
| Worktrees create no local DBs | ✅ PASS |
| Corruption probability reduced | ✅ PASS |
| Startup integrity checks | ✅ PASS |
| Broken DBs quarantined | ✅ PASS |
| User degraded-mode warnings | ⚠️ PARTIAL FAIL |
| Existing flows unaffected | ✅ PASS |

**Overall**: 9/10 criteria met. One criterion partially failed: the backend correctly signals degraded state, but the frontend `BoardPage.jsx` does not render the warning banner to the user.

**Blocking issue**: No — the platform is functional and resilient. The missing banner is a UX gap, not a correctness or reliability failure.

**Recommendation**: Add the `degraded` banner to `BoardPage.jsx` in a follow-up (reads `res.data.degraded` and renders: *"SQLite runtime database unavailable — showing filesystem-derived state"*). This is a small frontend-only change.
