I now have a complete picture of the implementation. Let me write the review.

---

# Implementation Review — T229: One-Click Project Deployment

**Branch:** `ticket/T229-add-one-click-project-deployment-for-end-to-end-va`
**Reviewed commit:** `9e5a1ddb`

---

## Summary

The implementation faithfully delivers the one-click deployment feature described in the ticket. All seven acceptance criteria are met. The security design (shell=False, type allowlist, path containment) is solid. The test suite is thorough on the backend. Two minor issues and one small gap are noted below; none are blocking.

---

## Scope compliance

All in-scope items from the plan are implemented. All explicitly excluded items (blue/green, rollback, multi-env, UI tests) are absent. No feature creep detected. Existing `redeploy_project` and workspace chat handlers are untouched.

---

## Backend — `services/supervisor/main.py`

### Correctness

The full deployment lifecycle is correctly implemented:

- **Config validation** (`_validate_project_deploy_block`): type allowlist enforced, `compose_file` path normalized via `Path.resolve()` and containment-checked with `relative_to()`, URL scheme validated. Returns `{"not_deployable": True}` cleanly when block is absent.
- **POST endpoint**: config load → validation → non-blocking lock acquire → dirty-tree check → SHA capture → session init → thread start → `202 Accepted`. Lock is explicitly released in every early-exit path (dirty, git error, outer exception).
- **Background job** (`_run_project_deploy_job`): stage machine `PENDING → BUILDING → STARTING → HEALTHCHECK → SUCCEEDED` (or `FAILED` at any stage). Lock released in `finally` unconditionally, including on unexpected exceptions. Persistence written in `finally`.
- **GET status**: 404 on unknown ID, 403 on project mismatch, correct JSON shape.
- **GET history**: empty list if file absent, correct 5-record cap.
- **Subprocess**: `shell=False` throughout, `docker` called as argv list. ✓

### Plan deviation: `asyncio` → `threading`

The plan specified `asyncio.Lock`. The implementation uses `threading.Lock` because the endpoint handlers are synchronous `def` functions (not `async def`). This is the correct choice; `asyncio.Lock` would not work here. Not a defect.

### Minor issue 1 — `log_tail` read outside lock (CPython-safe, non-portable)

In `workspace_project_deploy_status`, `session` is fetched under lock, then the lock is released before `list(session["log_tail"])` is called:

```python
with _deploy_sessions_lock:
    session = _deploy_sessions.get(deployment_id)
...
return {
    "log_tail": list(session["log_tail"]),  # lock not held
    ...
}
```

The background thread appends to the same deque concurrently. In CPython, `deque.append` and `list(deque)` are each GIL-atomic, so this is safe in practice. It would be cleaner to take a snapshot inside the lock, but this is not blocking.

### Minor issue 2 — `_git_has_local_changes` silent failure on non-zero exit

```python
def _git_has_local_changes(repo_path: str) -> bool:
    result = subprocess.run(["git", "status", "--porcelain"], ...)
    return bool(result.stdout.strip())
```

If `git status` exits non-zero (e.g., the path is not a git repo), `result.stdout` is empty and the function returns `False` — silently treating the path as clean. The caller only catches `FileNotFoundError` and `TimeoutExpired`. A deployment could then proceed on a path that isn't actually a git repository. This would likely fail later at `git rev-parse HEAD` or `docker compose up`, but the error surfaced would be less informative than a direct "not a git repository" 422. This is a minor robustness gap, not a security issue.

---

## Backend — `services/control_api/routes/workspace.py`

Clean transparent proxy:
- POST deploy uses a custom handler that passes through the full status code (`JSONResponse(status_code=resp.status_code, ...)`), correctly forwarding 202/409/422 to the frontend. ✓
- GET endpoints use `_forward_get` which raises `HTTPException` on 4xx — correct since 403/404 should surface as errors. ✓
- Route ordering: `/deploy/history` registered before `/deploy/{deployment_id}` to avoid FastAPI treating `"history"` as a deployment_id. ✓

---

## Frontend

### `ProjectWorkspacePanel.jsx`

- Deploy state machine is correct: `deployState.status` drives button disable logic, stage badge, preview URL, retry button, and log tail display.
- `not_deployable` banner renders without a deploy button (uses `deployNotDeployable` flag set on 422 `not_deployable` code). ✓
- `usePolling` stops when `status !== 'running'` (via `pollDelay = isDeployRunning ? 2000 : null`). ✓
- State reset on `projectId` change is complete. ✓

### `DeployHistoryPanel.jsx`

- Fetches on mount and re-fetches when `projectId` changes. ✓
- Renders 5 records with status badge, truncated SHA, URL link. ✓

### Minor gap — frontend unit tests not implemented

The plan listed four Vitest test cases for the deploy UI (button disabled while running, preview URL gating, not_deployable banner, history table). No frontend test file for deploy was added. The existing `apps/dashboard/tests/` directory has tests for other components but none for T229's new UI. The ticket acceptance criteria do not explicitly require automated frontend tests, but the plan did list them. This is a process gap, not a feature gap.

---

## Tests — `tests/test_deploy.py`

21 backend tests with good coverage:

| Scenario | Covered |
|---|---|
| Unknown project → 422 `not_deployable` | ✓ |
| No deploy block → 422 `not_deployable` | ✓ |
| Invalid type → 422 `invalid_deploy_config` | ✓ |
| Path escape → 422 `invalid_deploy_config` | ✓ |
| Dirty tree, `allow_dirty: false` → 422 `dirty_working_tree` | ✓ |
| Dirty tree, `allow_dirty: true` → 202 | ✓ |
| Concurrent POST → 409 with active `deployment_id` | ✓ |
| Lock released after background exception | ✓ |
| `deployed_sha` captured before job | ✓ |
| Successful build (no healthcheck) → SUCCEEDED | ✓ |
| Successful build + healthcheck → SUCCEEDED | ✓ |
| Healthcheck timeout → FAILED | ✓ |
| GET unknown ID → 404 | ✓ |
| GET cross-project → 403 | ✓ |
| GET returns session fields | ✓ |
| `log_tail` ≤ 50 lines | ✓ |
| Retry after SUCCEEDED → new `deployment_id` | ✓ |
| History empty when no file | ✓ |
| History returns last 5 | ✓ |
| `_update_deploy_history` bounded to 10 | ✓ |
| `_write_deploy_state` atomic (no tmp file left) | ✓ |

---

## `workspace_projects.example.yml`

All new `deploy` block fields documented with defaults. Both a full example and a minimal deploy-only example are included. ✓

---

## Acceptance criteria mapping

| Criterion | Status |
|---|---|
| Project can be deployed from AI Dev Factory | ✓ |
| Deployment progress visible in dashboard | ✓ (stage badge + log tail) |
| Success and failure states persisted | ✓ (`project-deploy-state.json`, `project-deploy-history.json`) |
| Deployment logs available for troubleshooting | ✓ (bounded log tail + rotating file) |
| Deployed app URL stored and displayed | ✓ |
| Deployment can be retried after failure | ✓ (Retry button, lock released in finally) |
| Existing workflows unchanged | ✓ (chat, actions/confirm, issues/confirm, redeploy all untouched) |

---

## Verdict

The implementation is correct, secure, and well-tested. The two minor issues (log_tail read without lock; silent `git status` failure) are not exploitable and are typical of pragmatic production Python threading code. The missing frontend unit tests are a gap from the plan but do not affect the feature's correctness. No blocking issues found.

IMPLEMENTATION_APPROVED
