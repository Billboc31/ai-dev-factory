All 43 tests pass. Here's a summary of the three fixes applied:

1. **`tools/agent_runner/run_ticket.py` (line 87-88)** — Added `"package.json"` and `"package-lock.json"` to `COMMIT_SCOPE`.

2. **`tests/test_commit_push.py`** — Added `test_commit_scope_contains_package_json()` asserting both new paths are in scope.

3. **`tests/test_run_daemon.py`** — Added `test_run_once_skips_test_complete_when_pr_skipped_no_diff()` with a state containing only `pr_skipped_no_diff=true` (no `daemon_archived`) to exercise the `run_once` guard independently of the `scan_tickets` filter.
