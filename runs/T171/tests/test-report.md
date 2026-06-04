---

## Test Report — T171

**Status: TEST_COMPLETE — VALIDATION FAILED (regression)**

### Acceptance Criteria: 6/6 PASS

| AC | Status |
|----|--------|
| Deploying T170 environment deploys T170 code | PASS |
| Runtime scripts come from the selected branch | PASS |
| Branch verification in deployment logs | PASS |
| Existing local worktrees no longer affect deployments | PASS |
| Failed clone/checkout aborts deployment clearly | PASS |
| Multiple environments can deploy different branches concurrently | PASS |

### Tests: 46/46 pass (T171 target suite)

All T171-specific and related tests are green.

### Regression: BLOCKING — 12 failures in `test_sandbox_worktree.py`

T171 renamed `create_with_worktree` → `create_with_source` but left `tests/test_sandbox_worktree.py` unchanged. All 12 tests calling `create_with_worktree` now throw `AttributeError`. These tests were passing on main before this branch.

**Required fix:** Delete `test_sandbox_worktree.py` (if worktree path is fully retired) or migrate its 12 tests to cover `create_with_source` equivalently.

### Pre-existing failures (not a T171 regression)

8 failures in `test_ticket_timeline.py` — existed on main before T171, caused by missing test data (404 from route), unrelated to this ticket.
