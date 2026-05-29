Clean. The changes are now strictly scoped to the two intended files.

**Summary of what was fixed:**

1. **Reverted all out-of-scope deletions/modifications** — restored 14 files (`environment_provision.py`, `environment_runner.py`, `sandbox_runtime_deploy.py`, `supervisor/main.py`, `routes/environments.py`, dashboard components, and related tests) back to `main`.

2. **Fixed the misleading log message** in `handle_test_complete()` (line 884): when `auto_merge_pr()` fails for non-conflict reasons and `detect_pr_conflict()` finds no conflict, the log now reads `"auto-merge failed but PR #N has no conflicts — no state transition needed"` instead of the misleading `"Failed to transition ticket ... to CONFLICT_RESOLUTION_NEEDED"`.

The core T162 fixes are intact: `handle_test_complete()` properly detects conflicts after failed merges, the branch-prefix PR fallback handles renamed branches, and all 35 PR lifecycle tests pass.
