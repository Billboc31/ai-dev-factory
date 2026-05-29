Here is the test report summary:

---

## T159 Tester Report — FAIL

**4 regressions introduced** (46 pre-existing failures unchanged).

### Acceptance criteria

| # | Criterion | Status |
|---|---|---|
| AC1 | Dashboard works if SQLite corrupt | PASS |
| AC2 | Daemon no infinite crash loop | PASS |
| AC3 | Filesystem fallback observable | PASS |
| AC4 | Single global runtime DB | PASS |
| AC5 | Worktrees don't create their own DBs | PASS |
| AC6 | Corruption probability reduced (WAL pragmas) | PASS |
| AC7 | Startup integrity checks | PASS |
| AC8 | Broken DBs quarantined automatically | PASS |
| AC9 | Explicit degraded-mode warnings | PASS |
| AC10 | Existing flows continue working | **PARTIAL FAIL** |

### Regressions (all 4 caused by the same root cause)

The new singleton guard (`_acquire_daemon_singleton` at `run_daemon.py:1831`) uses the real repo's `state_dir` (not the test's `tmp_path`), so in an environment where a daemon is already running, every test that calls `main()` without mocking the singleton guard exits early with code 1.

- `tests/test_run_daemon.py::test_main_once_returns_zero` — was PASS on main, now FAIL
- `tests/test_daemon_issue_polling.py::test_main_issue_label_passed_to_poll` — was PASS, now FAIL
- `tests/test_daemon_issue_polling.py::test_main_issue_repo_passed_to_poll` — was PASS, now FAIL
- `tests/test_daemon_issue_polling.py::test_main_default_issue_label_is_ai_ready` — was PASS, now FAIL

**Required fix**: add `patch("run_daemon._acquire_daemon_singleton", return_value=True)` to each of those 4 tests. The T159-specific SQLite tests (19/19) and dashboard API tests (23/23) all pass cleanly.
