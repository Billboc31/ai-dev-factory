# T159 — Tester Report

**Date**: 2026-05-29  
**Branch**: ticket/T159-t159-harden-runtime-sqlite-architecture-and-degrad  
**Verdict**: FAIL — 4 regressions introduced

---

## Test suite results

| Suite | Passed | Failed | Notes |
|---|---|---|---|
| `tests/test_runtime_db.py` | 19/19 | 0 | All T159-specific SQLite tests pass |
| `tests/test_runtime_dashboard_api.py` | 23/23 | 0 | All dashboard API tests pass |
| `tests/test_daemon_issue_polling.py` | 45/49 | **4** | 3 regressions from T159 + 1 pre-existing |
| `tests/test_run_daemon.py` | 44/46 | **2** | 1 regression from T159 + 1 pre-existing |
| `tests/test_daemon_checkpoint.py` | 25/30 | 5 | All pre-existing |
| `tests/test_ticket_timeline.py` | 0/8 | 8 | All pre-existing |
| All other suites | ~1005/1021 | ~16 | Pre-existing |

**Total**: 1171 pass, 50 fail (46 pre-existing, **4 regressions from T159**)

---

## Acceptance criteria

### AC1 — Runtime dashboard still works if SQLite becomes corrupted
**PASS**

- `board_service.py:125–238`: SQLite primary with full JSON fallback for workers, ticket state, issue index
- `BoardResponse.degraded: bool` returned in API when fallback is active
- Frontend `BoardPage.jsx:103–106`: displays "SQLite runtime database unavailable — showing filesystem-derived runtime state" when `degraded=True`

### AC2 — Daemon does not enter infinite crash/retry loops on malformed DB
**PASS**

- `runtime_db.py:124–188`: `check_and_recover_db()` detects corruption, quarantines, attempts recovery, falls back to recreating empty DB — always returns cleanly
- `run_daemon.py:123–137`: `_ensure_db()` catches all exceptions and returns `None` on failure; daemon continues without SQLite
- `test_check_and_recover_db_corrupt_db_quarantined`: PASS

### AC3 — Runtime state remains observable through filesystem fallback
**PASS**

- `board_service.py:133–137`: falls back to `workers.json` when SQLite workers query fails
- `board_service.py:169–173`: falls back to per-ticket `state.json` when SQLite ticket_runtime fails
- `board_service.py:233–238`: falls back to `.issue-intake.json` when SQLite issue index fails
- Union of filesystem-discovered tickets and SQLite-known tickets ensures no tickets are lost

### AC4 — Only one global runtime DB is used
**PASS**

- `runtime_db.py:73–102`: `get_db_path()` resolves via `git rev-parse --git-common-dir` → always points to main repo's `.runtime/ai-dev-factory.sqlite`
- Docker path: `$AI_DEV_FACTORY_RUNTIME_ROOT/.runtime/ai-dev-factory.sqlite`
- Single cached path per daemon process (`_DB_PATH_VALUE`)

### AC5 — Worktrees no longer create runtime SQLite DBs
**PASS**

- `get_db_path()` uses `--git-common-dir` which resolves to main repo regardless of which worktree the module is loaded from
- Worktree creation code does not call `init_runtime_db()`
- Verified: no `.runtime/` creation in worktree init paths

### AC6 — SQLite corruption probability is significantly reduced
**PASS**

- `runtime_db.py:109–111` (init) and `:118–120` (every connection): `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `PRAGMA synchronous=NORMAL`
- `test_check_and_recover_db_pragmas`: PASS

### AC7 — Startup integrity checks run automatically
**PASS**

- `run_daemon.py:131`: `_rdb_check_and_recover(db_path)` called at daemon startup via `_ensure_db()` before `_rdb_init()`
- `runtime_db.py:147–152`: runs `PRAGMA integrity_check`, short-circuits to True on `"ok"`
- `test_check_and_recover_db_healthy_db`: PASS

### AC8 — Broken DBs are quarantined automatically
**PASS**

- `runtime_db.py:156–165`: corrupt DB renamed to `ai-dev-factory.sqlite.corrupt.YYYYMMDDTHHmmSSZ` automatically
- Logged explicitly: `"[runtime_db] DB corrupt — entering degraded mode"` and quarantine filename
- `test_check_and_recover_db_corrupt_db_quarantined`: PASS

### AC9 — Users receive explicit degraded-mode warnings
**PASS**

- Console: `"[runtime_db] DB corrupt — entering degraded mode"` at recovery time
- API: `BoardResponse.degraded: bool` and `RuntimeHealth.sqlite_degraded: bool` in all relevant endpoints
- UI: BoardPage displays yellow banner "SQLite runtime database unavailable — showing filesystem-derived runtime state" when `degraded=True`

### AC10 — Existing deploy/sandbox/runtime flows continue functioning
**PARTIAL FAIL — regressions detected**

See regressions section below. The daemon's `--once` mode (used by issue polling and standard one-shot runs) breaks when another daemon instance is running in the environment.

---

## Regressions

### REGRESSION 1 — `test_main_once_returns_zero` (CRITICAL)

**File**: `tests/test_run_daemon.py:324`  
**Status on main**: PASS  
**Status on T159**: FAIL — `assert 1 == 0`

**Root cause**: The new singleton guard (`_acquire_daemon_singleton` at `run_daemon.py:1831`) detects the live daemon process holding `state/daemon-singleton.lock` in the dev environment and returns 1. The test does not mock `_acquire_daemon_singleton` and uses the real repo's `state_dir` (not the test's `tmp_path`).

**Impact**: The `--once` mode of the daemon returns exit code 1 instead of 0 when a daemon is already running. This breaks any CI/test environment where a daemon process is alive.

---

### REGRESSION 2–4 — `test_daemon_issue_polling` (3 tests)

**File**: `tests/test_daemon_issue_polling.py`  
**Tests**: `test_main_issue_label_passed_to_poll`, `test_main_issue_repo_passed_to_poll`, `test_main_default_issue_label_is_ai_ready`  
**Status on main**: PASS  
**Status on T159**: FAIL — `TypeError: 'NoneType' object is not subscriptable` (mock_poll.call_args is None)

**Root cause**: Same as above. The singleton guard causes `main()` to return 1 before reaching the `poll_github_issues()` call. The mock is never called, so `call_args` is `None`.

**Stderr evidence**:
```
[daemon] another daemon instance is already running (singleton lock held) — exiting cleanly
```

---

## Required fix

The singleton guard must not block test execution. Tests calling `main()` that do not intend to test the singleton behavior must either:
- Mock `_acquire_daemon_singleton` to return `True`, or
- Pass a test-local `state_dir` so the lock file doesn't collide with the live daemon

Example minimal fix in `test_main_once_returns_zero`:
```python
with patch("run_daemon._check_runtime_clone", return_value=True), \
     patch("run_daemon._acquire_daemon_singleton", return_value=True):
    rc = main(["--exec-cmd", "test-cmd", "--once", "--runs-dir", str(runs)])
assert rc == 0
```

The same fix applies to the 3 affected issue-polling tests.

---

## Non-blocking observations

- `_try_load_runtime_db` returns `degraded=False` when DB is absent (not initialized). This is intentional but means the degraded banner won't appear in a fresh environment before the first daemon run — acceptable behavior.
- `test_check_and_recover_db_lock_serialization` (concurrent recovery) passes with 4 threads.
- Board service degraded flag is set lazily per failed query, meaning partial failures are correctly surfaced.
