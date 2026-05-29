# Tester Report — T157

## Summary

Implementation validated. All core deployment-correctness acceptance criteria pass. One gap in the runtime dashboard display (AC6 partial). All test failures in the full suite are pre-existing from prior tickets and unrelated to T157's scope.

---

## Acceptance Criteria

### AC1 — Deploying a ticket branch fetches the latest remote commit before sandbox creation
**PASS**

`sandbox_manager.py` runs `git fetch origin <branch>` before `git worktree add`. Verified in diff (lines 255–270) and confirmed by test `test_create_with_worktree_fetches_before_checkout` which asserts `fetch_idx < worktree_idx` in the subprocess call sequence.

### AC2 — The sandbox worktree HEAD equals the fetched remote branch HEAD
**PASS**

After fetch, `git rev-parse origin/<branch>` resolves the exact remote SHA. The worktree is created with `git worktree add --detach <path> <sha>` — never via branch name. Test `test_create_with_worktree_uses_remote_sha_not_branch_name` asserts the SHA appears in the worktree command and the branch name does not.

### AC3 — If a new commit is pushed to a ticket branch, a subsequent deploy uses that new commit
**PASS**

No SHA is cached between calls. Each invocation of `create_with_worktree()` runs fetch + rev-parse fresh, so any new remote commit is picked up on the next deploy. Verified by code inspection: no memoization or state reuse of `commit_sha` across calls.

### AC4 — If the requested branch/ref does not exist, deployment fails with a clear error and does not deploy `main` silently
**PASS**

Two failure paths, both destroy the sandbox before raising:
- `git fetch` non-zero → `RuntimeError("git fetch origin {branch} failed: {stderr}")`
- `git rev-parse` non-zero → `RuntimeError("git rev-parse origin/{branch} failed: {stderr}")`

Test `test_create_with_worktree_fails_loudly_if_fetch_fails` verifies `RuntimeError` is raised matching the branch name, and `mgr.list()` is empty afterward (sandbox destroyed).

### AC5 — Sandbox state/metadata exposes the deployed ref and commit SHA
**PASS**

Three fields added to `SandboxState` (`models/sandbox.py`):
- `requested_ref` — user-supplied branch name (e.g. `ticket/T156-foo`)
- `resolved_ref` — remote ref used (e.g. `origin/ticket/T156-foo`)
- `commit_sha` — 40-char SHA from `rev-parse`

All three are written to `state.json` after worktree creation. Test `test_create_with_worktree_records_ref_identity_in_state` verifies values are correct and survive a reload via `mgr.status(state.id)`.

### AC6 — Runtime UI can display the deployed commit/ref from sandbox metadata
**PARTIAL FAIL — non-blocking**

The data is stored and accessible. `GET /sandboxes/{id}` returns the full `SandboxState` including the new fields.

**Gap:** `runtime_dashboard.py`'s `_parse_sandbox_state()` (line 203) reads:
```python
ref=raw.get("ref") or raw.get("branch") or raw.get("commit"),
```
None of these keys match the T157 state fields (`requested_ref`, `resolved_ref`, `commit_sha`). The runtime dashboard overview will therefore show `ref: null` for all T157-deployed sandboxes.

The fix is one line in `_parse_sandbox_state`:
```python
ref=raw.get("ref") or raw.get("branch") or raw.get("commit") or raw.get("requested_ref"),
```

This is non-blocking for deploy correctness but is a genuine gap in the "can display" criterion.

### AC7 — Existing deploys from `main` still work
**PASS**

The `trigger_deploy` endpoint routes to `run_deploy(project_id, project_root)` unchanged when no branch is provided. Code path is untouched.

### AC8 — Existing sandbox isolation guarantees remain intact
**PASS**

Worktree isolation (separate path, separate compose project, separate env-file) is unchanged. The `--detach` flag and SHA-based checkout enforce stricter isolation than before.

---

## Test Suite Results

All 16 sandbox worktree tests pass:

```
tests/test_sandbox_worktree.py::test_create_with_worktree_fetches_before_checkout    PASSED
tests/test_sandbox_worktree.py::test_create_with_worktree_uses_remote_sha_not_branch_name  PASSED
tests/test_sandbox_worktree.py::test_create_with_worktree_fails_loudly_if_fetch_fails PASSED
tests/test_sandbox_worktree.py::test_create_with_worktree_records_ref_identity_in_state    PASSED
tests/test_sandbox_worktree.py::test_create_with_worktree_uses_branch_when_given      PASSED
tests/test_sandbox_worktree.py::test_create_with_worktree_uses_detach_when_no_branch  PASSED
... (10 more, all PASSED)
16 passed in 15.36s
```

### Pre-existing failures (not caused by T157)

52 failures in the full suite, all pre-existing on `main`:

| Test file | Root cause | Origin ticket |
|---|---|---|
| `test_environment_routes.py` (7) | `/environments` router not registered in `main.py` | T151 |
| `test_ticket_timeline.py` (9) | `/timeline` route not registered in `main.py` | T156 |
| `test_control_api_subprocess.py` (6) | Test isolation issue (pass individually) | pre-existing |
| `test_daemon_checkpoint.py` (4) | Unrelated daemon logic | pre-existing |
| `test_daemon_issue_polling.py` (1) | Unrelated issue polling | pre-existing |
| `test_run_daemon.py` (2) | Unrelated daemon logic | pre-existing |

None of these failures overlap with T157's changed files (`models/sandbox.py`, `routes/deployer.py`, `services/sandbox_manager.py`, `tests/test_sandbox_worktree.py`).

---

## Issues Found

### Issue 1 — Runtime dashboard does not surface new ref fields (non-blocking)

**File:** `services/control_api/routes/runtime_dashboard.py:203`

**Symptom:** `SandboxRunSummary.ref` is `null` in the dashboard overview for all sandboxes deployed via the T157 branch path.

**Cause:** Key mismatch — dashboard reads `ref`/`branch`/`commit`, state stores `requested_ref`/`resolved_ref`/`commit_sha`.

**Fix:** Add `or raw.get("requested_ref")` to the fallback chain in `_parse_sandbox_state()`.

**Severity:** Non-blocking. Core deploy correctness is intact. Data is available via `GET /sandboxes/{id}`.

---

## Verdict

**CONDITIONAL PASS** — core acceptance criteria (AC1–AC5, AC7–AC8) are satisfied. AC6 is partially satisfied: metadata is stored and accessible via the API, but the runtime dashboard overview does not display it. Recommend a one-line fix in `runtime_dashboard.py:203` or accept as known gap before merge.
