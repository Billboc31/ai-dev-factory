I have all the information needed. Here is the test report.

---

## Test Report — T031

**Branch**: `ticket/T031-daemon-terminal-skip-commit-hardening`
**Test suite**: 96 tests collected — **95 passed, 1 failed**

---

### Acceptance criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|---------|
| 1 | Old `TEST_COMPLETE` tickets no longer slow the daemon | **PASS** | `test_run_once_skips_test_complete_when_issue_closed`, `test_run_once_skips_test_complete_when_pr_skipped_no_diff` |
| 2 | Ticket marked `daemon_archived=true` is ignored | **PASS** | `test_scan_tickets_skips_daemon_archived` + `test_scan_tickets_skips_daemon_archived_logs_message` — log message `skipping T022 daemon_archived=true` confirmed |
| 3 | PR impossible (no diff) is not retried in a loop | **PASS** | `test_create_or_update_pr_marks_pr_skipped_no_diff_on_no_commits_error` — `pr_skipped_no_diff=True` and `daemon_archived=True` both written atomically |
| 4 | Commit API/button commits expected code changes | **FAIL** | `test_commit_with_include_code_stages_all_scope_paths` fails (see below) |
| 5 | Workspace can stay clean after UI action | **PASS** | `test_commit_without_include_code_stages_only_run_dir`, `test_commit_succeeds_on_correct_branch` |
| 6 | No dangerous git logic (`git add .`) | **PASS** | `test_commit_never_calls_git_add_dot` |
| 7 | Logs are explicit | **PASS** | Log messages verified in daemon skip, archive, and PR no-diff tests |
| 8 | Existing workflow remains compatible | **PASS** | All 27 daemon tests and 14 PR lifecycle tests pass |

---

### Failing test analysis

**Test**: `test_commit_with_include_code_stages_all_scope_paths` (`tests/test_commit_push.py:224`)

**What it checks**: when `commit_ticket(..., include_code=True)` is called, every path in `COMMIT_SCOPE` should be passed to `git add`.

**What fails**: the test uses a bare `tempfile.TemporaryDirectory()` and only creates `runs/T999/state.json`. None of the COMMIT_SCOPE directories (`tools/`, `tests/`, `apps/`, etc.) are created. The implementation correctly skips paths that do not exist on disk (`stage_paths = [path for path in requested_stage_paths if Path(path).exists()]`), so only `runs/T999/` and `runs/` are staged.

**Root cause**: the test does not set up the expected directory structure before asserting.

**Classification**: **test defect, not an implementation defect**. The implementation behavior (skip non-existent paths rather than blindly calling `git add nonexistent/`) is correct and intentional. In the real repo all COMMIT_SCOPE directories exist and are staged correctly. The parallel test `test_commit_scope_contains_apps_and_services` passes and confirms the scope declaration is correct.

**Fix required**: create stub paths for each `COMMIT_SCOPE` entry inside the temp directory before calling `commit_ticket`, e.g.:

```python
for p in COMMIT_SCOPE:
    (Path(tmp) / p).mkdir(parents=True, exist_ok=True)
```

---

### Summary

The implementation satisfies all acceptance criteria. The single failing test is a test setup defect: it does not create the required directory structure before verifying staging behaviour. No implementation change is needed; the test needs a one-line fixture fix.

**Verdict**: **FAIL** — 1 test defect must be corrected before this can be considered clean. The defect is non-critical (the underlying feature is correct), but the test suite must be green before moving to the next workflow step.
